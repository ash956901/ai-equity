"""Generate AI one-line summaries for filings.

Powers the Timeline feed -- replaces the static
``f"{filing.filing_type} filed on {filing.filing_date}"`` template with
"Capex spend up 40% YoY", "Auditor change disclosed", or "Q3 PAT down 18%
on inventory write-down" style headlines.

Idempotent: result is upserted into ``filing_summaries`` by ``filing_id``.
Falls back to a deterministic heuristic when no LLM is available so the
pipeline still produces *something* useful for every filing.
"""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.db.database import SessionLocal
from src.db.models import Filing, FilingPage, FilingSummary

logger = logging.getLogger(__name__)


# Coarse mapping from filing_type → default event_type when the LLM
# cannot classify or returns garbage.
_DEFAULT_EVENT_BY_TYPE: dict[str, str] = {
    "Annual_Report": "annual_report",
    "Quarterly_Results": "quarterly_results",
    "Investor_Presentation": "investor_presentation",
    "Earnings_Call": "earnings_call",
    "Board_Meeting": "board_action",
    "Shareholding_Pattern": "shareholding",
    "Corporate_Action": "corporate_action",
    "Press_Release": "press_release",
}

VALID_EVENT_TYPES = {
    "quarterly_results",
    "annual_report",
    "investor_presentation",
    "earnings_call",
    "board_action",
    "shareholding",
    "corporate_action",
    "press_release",
    "capex_announcement",
    "guidance_change",
    "management_change",
    "acquisition",
    "debt_raise",
    "debt_default",
    "regulatory_action",
    "auditor_change",
    "dividend",
    "buyback",
    "qip",
    "other",
}


def _llm_available() -> bool:
    try:
        from src.config import get_settings

        s = get_settings()
        if s.llm_provider == "ollama" and s.ollama_base_url == "http://localhost:11434":
            return False
        if s.llm_provider == "openai" and not s.openai_api_key:
            return False
        if s.llm_provider == "groq" and not s.groq_api_key:
            return False
        if s.llm_provider == "deepseek" and not s.deepseek_api_key:
            return False
        return True
    except Exception:
        return False


def _gather_filing_text(db, filing_id: UUID, max_chars: int = 12000) -> str:
    pages = (
        db.query(FilingPage)
        .filter(FilingPage.filing_id == filing_id)
        .order_by(FilingPage.page_number.asc())
        .limit(20)
        .all()
    )
    parts: list[str] = []
    total = 0
    for p in pages:
        if not p.text:
            continue
        snippet = p.text.strip()
        if not snippet:
            continue
        parts.append(snippet[:1500])
        total += len(snippet[:1500])
        if total >= max_chars:
            break
    return "\n\n".join(parts)


def _heuristic_one_liner(filing: Filing) -> str:
    """Deterministic fallback when no LLM is configured."""
    title = (filing.title or "").strip()
    fdate = filing.filing_date.isoformat() if filing.filing_date else "?"
    if title and len(title) <= 110:
        return title
    if title:
        return title[:107].rstrip() + "..."
    return f"{filing.filing_type or 'Filing'} dated {fdate}"


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _call_llm_summary(filing: Filing, body: str) -> Dict[str, Any]:
    """Ask the LLM for a tight one-liner + event_type + materiality."""
    fallback = {
        "summary": _heuristic_one_liner(filing),
        "event_type": _DEFAULT_EVENT_BY_TYPE.get(filing.filing_type or "", "other"),
        "materiality_score": 0.4,
        "sentiment": "neutral",
        "affected_dimension": None,
    }
    if not body or not _llm_available():
        return fallback

    try:
        from src.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm(temperature=0.1)
        prompt = (
            f"Filing type: {filing.filing_type}\n"
            f"Filing date: {filing.filing_date.isoformat() if filing.filing_date else '?'}\n"
            f"Title: {filing.title or ''}\n\n"
            f"--- BODY (truncated) ---\n{body[:8000]}\n--- END BODY ---\n\n"
            "Produce a single one-line summary an analyst would scroll past in a "
            "Bloomberg-style timeline. Lead with the news (numbers, names, %, "
            "directionality), not the form name. Max 110 characters.\n\n"
            "Respond with STRICT JSON ONLY:\n"
            "{\n"
            '  "summary": "...one line, <=110 chars...",\n'
            '  "event_type": "quarterly_results|annual_report|investor_presentation|'
            "earnings_call|board_action|shareholding|corporate_action|press_release|"
            "capex_announcement|guidance_change|management_change|acquisition|"
            'debt_raise|debt_default|regulatory_action|auditor_change|dividend|buyback|qip|other",\n'
            '  "materiality_score": 0.0-1.0,    // 0=admin, 1=major thesis-changing event\n'
            '  "sentiment": "positive|negative|neutral",\n'
            '  "affected_dimension": "earnings|guidance|management|regulation|capex|leverage|liquidity|other"\n'
            "}"
        )
        msgs = [
            SystemMessage(
                content=(
                    "You write extremely terse one-line filing summaries for an "
                    "Indian-equity research timeline. No fluff."
                )
            ),
            HumanMessage(content=prompt),
        ]
        resp = llm.invoke(msgs)
        parsed = _parse_json_block(getattr(resp, "content", "") or "")
        if not parsed:
            return fallback

        summary = (parsed.get("summary") or "").strip()
        if not summary:
            summary = fallback["summary"]
        if len(summary) > 110:
            summary = summary[:107].rstrip() + "..."

        event_type = (parsed.get("event_type") or "other").strip()
        if event_type not in VALID_EVENT_TYPES:
            event_type = fallback["event_type"]
        try:
            materiality = max(
                0.0, min(1.0, float(parsed.get("materiality_score") or 0.4))
            )
        except (TypeError, ValueError):
            materiality = 0.4
        sentiment = (parsed.get("sentiment") or "neutral").strip()
        if sentiment not in {"positive", "negative", "neutral"}:
            sentiment = "neutral"
        affected = parsed.get("affected_dimension")
        if isinstance(affected, str):
            affected = affected.strip()[:50] or None
        return {
            "summary": summary,
            "event_type": event_type,
            "materiality_score": materiality,
            "sentiment": sentiment,
            "affected_dimension": affected,
        }
    except Exception as exc:
        logger.debug("filing summary LLM failed; using heuristic: %s", exc)
        return fallback


def summarize_filing(filing_id: UUID) -> Dict[str, Any]:
    """Generate and persist a one-line summary for a single filing."""
    db = SessionLocal()
    try:
        filing = db.query(Filing).filter(Filing.id == filing_id).first()
        if not filing:
            return {"filing_id": str(filing_id), "status": "missing"}

        body = _gather_filing_text(db, filing_id)
        result = _call_llm_summary(filing, body)

        existing = (
            db.query(FilingSummary)
            .filter(FilingSummary.filing_id == filing_id)
            .first()
        )
        from src.config import get_settings

        model_used = get_settings().get_llm_model() if _llm_available() else "heuristic"
        payload = {
            "summary_one_liner": result["summary"],
            "event_type": result["event_type"],
            "materiality_score": Decimal(str(result["materiality_score"])),
            "sentiment": result["sentiment"],
            "affected_dimension": result["affected_dimension"],
            "model_used": model_used,
        }
        if existing is None:
            db.add(FilingSummary(filing_id=filing_id, **payload))
        else:
            for k, v in payload.items():
                setattr(existing, k, v)
        db.commit()
        return {"filing_id": str(filing_id), "status": "ok", **payload, "materiality_score": float(payload["materiality_score"])}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def summarize_pending_filings(batch_size: int = 50) -> Dict[str, Any]:
    """Summarise all parsed filings that don't yet have a FilingSummary row."""
    db = SessionLocal()
    try:
        rows = (
            db.query(Filing.id)
            .outerjoin(FilingSummary, FilingSummary.filing_id == Filing.id)
            .filter(FilingSummary.filing_id.is_(None))
            .filter(Filing.status.in_(("parsed", "embedded")))
            .order_by(Filing.filing_date.desc().nullslast())
            .limit(batch_size)
            .all()
        )
        ids: List[UUID] = [r.id for r in rows]
    finally:
        db.close()

    summarised = 0
    for fid in ids:
        try:
            summarize_filing(fid)
            summarised += 1
        except Exception as exc:
            logger.warning("summarize_filing failed for %s: %s", fid, exc)
    return {"considered": len(ids), "summarised": summarised}
