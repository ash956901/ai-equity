"""Theme tagging agent.

For each company, this agent:

1. Pulls the curated theme taxonomy.
2. Searches recent filings, news, and transcripts in Qdrant for keyword/
   semantic matches against each theme.
3. Optionally calls the LLM (when ``llm_provider`` is configured with a key)
   to classify exposure as ``direct | input | customer | substitute`` with a
   1-2 sentence rationale.
4. Persists ``CompanyTheme`` rows and emits matching ``relation_edges``.

The LLM call is optional and gracefully falls back to a deterministic
heuristic so the pipeline runs without a key.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import (
    Company,
    CompanyTheme,
    Filing,
    FilingPage,
    NewsArticle,
    RelationEdge,
    Transcript,
    TranscriptSegment,
)
from src.etl.theme_taxonomy_loader import list_themes
from src.services.vector_service import VectorService

logger = logging.getLogger(__name__)


VALID_EXPOSURE = {"direct", "input", "customer", "substitute", "derivative", "second_order"}
VALID_DIRECTIONS = {"+", "-", "neutral"}
VALID_HORIZONS = {"short", "medium", "long"}

# Confidence floor for persisting a theme. Tagger drops candidates below this
# unless evidence is overwhelming (>=4 keyword matches AND >=2 quotes).
MIN_CONFIDENCE = 0.55
MIN_EVIDENCE_QUOTES = 2


def _gather_company_text(db: Session, company_id: UUID, lookback_days: int) -> Dict[str, List[str]]:
    """Pull recent text snippets for a company from filings/news/transcripts."""
    since = datetime.utcnow() - timedelta(days=lookback_days)

    snippets: Dict[str, List[str]] = {"filings": [], "news": [], "transcripts": []}

    filing_pages = (
        db.query(FilingPage, Filing)
        .join(Filing, FilingPage.filing_id == Filing.id)
        .filter(Filing.company_id == company_id)
        .filter(Filing.created_at >= since)
        .limit(60)
        .all()
    )
    for page, _ in filing_pages:
        if page.text:
            snippets["filings"].append(page.text[:1500])

    news = (
        db.query(NewsArticle)
        .filter(NewsArticle.company_id == company_id)
        .filter(NewsArticle.published_at >= since)
        .order_by(NewsArticle.published_at.desc())
        .limit(40)
        .all()
    )
    for n in news:
        snippets["news"].append((n.headline or "") + ". " + (n.body or "")[:600])

    segs = (
        db.query(TranscriptSegment, Transcript)
        .join(Transcript, TranscriptSegment.transcript_id == Transcript.id)
        .filter(Transcript.company_id == company_id)
        .filter(Transcript.created_at >= since)
        .limit(80)
        .all()
    )
    for seg, _ in segs:
        if seg.text:
            snippets["transcripts"].append(seg.text[:1500])

    return snippets


def _keyword_score(theme_keywords: List[str], texts: List[str]) -> Dict[str, Any]:
    """Return a deterministic match summary for a theme's keywords."""
    if not theme_keywords or not texts:
        return {"score": 0.0, "matches": 0, "snippets": []}
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in theme_keywords if k) + r")\b",
        re.IGNORECASE,
    )
    matches = 0
    snippets: List[str] = []
    for txt in texts:
        if not txt:
            continue
        for m in pattern.finditer(txt):
            matches += 1
            start = max(0, m.start() - 80)
            end = min(len(txt), m.end() + 120)
            snippets.append(txt[start:end].strip())
            if len(snippets) >= 3:
                break
        if len(snippets) >= 3:
            break
    return {
        "score": min(1.0, matches / 8.0),
        "matches": matches,
        "snippets": snippets[:3],
    }


def _llm_available() -> bool:
    """Return True only when a usable LLM is configured."""
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


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from ``text``."""
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _call_llm_classifier(
    company: Company, theme: Dict[str, Any], snippets: List[str]
) -> Dict[str, Any]:
    """LLM-based exposure classifier with structured-output schema.

    Returns a dict with::

        {
            "exposure": "direct|input|customer|supplier|substitute|derivative|second_order",
            "impact": float (0..1),
            "impact_direction": "+|-|neutral",
            "impact_horizon": "short|medium|long",
            "evidence_quotes": [str, ...],   # >= MIN_EVIDENCE_QUOTES on success
            "reasoning": str,
        }

    Falls back to a sensible default when no LLM is available.
    """
    fallback = {
        "exposure": "direct",
        "impact": 0.5,
        "impact_direction": "+",
        "impact_horizon": "medium",
        "evidence_quotes": [s[:240] for s in (snippets or [])[:2]],
        "reasoning": (
            f"{company.name} mentions {theme['label']} in recent disclosures."
        ),
    }
    if not snippets or not _llm_available():
        return fallback

    try:
        from src.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm(temperature=0.1)
        snippet_block = "\n---\n".join(snippets[:4])
        prompt = (
            f"Company: {company.name} "
            f"(sector={company.sector or '?'} industry={company.industry or '?'})\n"
            f"Theme: {theme['label']} (code={theme['code']})\n"
            f"Theme description: {theme.get('description','')}\n\n"
            f"Evidence snippets from filings/news/transcripts:\n{snippet_block}\n\n"
            "Classify this company's exposure to the theme. Reject the theme if "
            "evidence is weak, generic, or off-topic — it is better to skip than "
            "to over-tag.\n\n"
            "Respond with STRICT JSON. No prose, no markdown:\n"
            "{\n"
            '  "exposure": "direct|input|customer|supplier|substitute|derivative|second_order",\n'
            '  "impact": 0.0-1.0,             // economic significance to the firm\n'
            '  "impact_direction": "+|-|neutral",\n'
            '  "impact_horizon": "short|medium|long",\n'
            '  "evidence_quotes": ["quote 1", "quote 2"],   // verbatim excerpts you used\n'
            '  "reasoning": "1-2 sentence explanation"\n'
            "}\n\n"
            "If evidence is insufficient, set exposure=\"direct\" and impact<=0.2 — "
            "the caller will drop it."
        )
        msgs = [
            SystemMessage(
                content=(
                    "You are an Indian-equity buy-side analyst classifying "
                    "thematic exposure with rigorous evidence standards."
                )
            ),
            HumanMessage(content=prompt),
        ]
        resp = llm.invoke(msgs)
        text = getattr(resp, "content", "") or ""
        parsed = _parse_json_block(text)
        if not parsed:
            return fallback

        exposure = (parsed.get("exposure") or "direct").lower()
        if exposure not in VALID_EXPOSURE:
            exposure = "direct"
        try:
            impact = max(0.0, min(1.0, float(parsed.get("impact"))))
        except (TypeError, ValueError):
            impact = 0.5
        direction = (parsed.get("impact_direction") or "+").strip()
        if direction not in VALID_DIRECTIONS:
            direction = "+"
        horizon = (parsed.get("impact_horizon") or "medium").strip().lower()
        if horizon not in VALID_HORIZONS:
            horizon = "medium"
        quotes_raw = parsed.get("evidence_quotes") or []
        if isinstance(quotes_raw, str):
            quotes_raw = [quotes_raw]
        quotes = [str(q)[:300] for q in quotes_raw if q][:5]
        if not quotes:
            quotes = [s[:240] for s in snippets[:2]]
        reasoning = (parsed.get("reasoning") or "").strip() or fallback["reasoning"]
        return {
            "exposure": exposure,
            "impact": impact,
            "impact_direction": direction,
            "impact_horizon": horizon,
            "evidence_quotes": quotes,
            "reasoning": reasoning,
        }
    except Exception as exc:
        logger.debug("LLM classifier failed; using heuristic: %s", exc)
        return fallback


def _call_asymmetric_validator(
    company: Company,
    theme: Dict[str, Any],
    classification: Dict[str, Any],
) -> bool:
    """Second LLM pass: is this exposure non-obvious / asymmetric?

    Returns True only when the LLM judges the exposure to be a
    Castrol-style insight — not derivable from the company's primary
    sector/industry alone. Heuristic fallback marks any
    ``derivative``/``second_order``/``supplier`` exposure with impact >=0.4
    as asymmetric.
    """
    exposure = classification.get("exposure", "direct")
    impact = float(classification.get("impact") or 0.0)

    heuristic = (
        exposure in {"derivative", "second_order", "supplier"} and impact >= 0.4
    )

    if not _llm_available():
        return heuristic

    try:
        from src.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm(temperature=0.0)
        prompt = (
            f"Company: {company.name} "
            f"(sector={company.sector or '?'} industry={company.industry or '?'})\n"
            f"Theme: {theme['label']} (code={theme['code']})\n"
            f"Exposure type: {exposure}\n"
            f"Impact: {impact:.2f}  Direction: {classification.get('impact_direction')}\n"
            f"Reasoning: {classification.get('reasoning')}\n\n"
            "Is this exposure ASYMMETRIC — meaning it would NOT be obvious from "
            "the company's primary sector/industry alone, but emerges from a "
            "second-order or supply-chain link (e.g. Castrol India → Data Centres "
            "via specialty coolants)?\n\n"
            'Respond with STRICT JSON: {"asymmetric": true|false, "why": "1 line"}'
        )
        msgs = [
            SystemMessage(
                content=(
                    "You judge whether thematic exposure is non-obvious to retail "
                    "investors. Be conservative — only mark asymmetric when the "
                    "company's primary classification would not flag the theme."
                )
            ),
            HumanMessage(content=prompt),
        ]
        resp = llm.invoke(msgs)
        parsed = _parse_json_block(getattr(resp, "content", "") or "")
        if not parsed:
            return heuristic
        return bool(parsed.get("asymmetric"))
    except Exception as exc:
        logger.debug("asymmetric validator failed; using heuristic: %s", exc)
        return heuristic


class ThemeTaggingAgent:
    """Tag company exposure to taxonomy themes."""

    def __init__(self, *, lookback_days: int = 30, vector_service: Optional[VectorService] = None):
        self.lookback_days = lookback_days
        self.vector_service = vector_service or VectorService()

    def tag_company(self, company_id: UUID, *, db: Optional[Session] = None) -> Dict[str, Any]:
        own = db is None
        db = db or SessionLocal()
        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return {"company_id": str(company_id), "themes": 0, "status": "missing"}

            themes = list_themes()
            if not themes:
                return {"company_id": str(company_id), "themes": 0, "status": "no_taxonomy"}

            snippets_by_source = _gather_company_text(db, company_id, self.lookback_days)
            all_snippets = (
                snippets_by_source["filings"]
                + snippets_by_source["news"]
                + snippets_by_source["transcripts"]
            )
            if not all_snippets:
                return {"company_id": str(company_id), "themes": 0, "status": "no_evidence"}

            applied = 0
            asymmetric = 0
            applied_codes: set[str] = set()
            for theme in themes:
                summary = _keyword_score(theme.get("keywords") or [], all_snippets)

                # Augment with semantic search when keyword evidence is thin.
                if summary["matches"] < 2 and summary["score"] < 0.2:
                    semantic = self.vector_service.search_company_filings(
                        company_id=company_id,
                        query=theme["label"],
                        limit=3,
                    )
                    semantic_snippets = [
                        (h.get("text") or "")[:1000] for h in semantic if h.get("text")
                    ]
                    semantic_score = (
                        max((float(h.get("score") or 0.0) for h in semantic), default=0.0)
                        if semantic_snippets
                        else 0.0
                    )
                    if semantic_score < 0.55 and summary["matches"] == 0:
                        continue
                    summary["snippets"] = semantic_snippets[:2] or summary["snippets"]
                    summary["score"] = max(summary["score"], semantic_score - 0.2)

                classified = _call_llm_classifier(company, theme, summary["snippets"])
                impact = float(classified["impact"])
                evidence_quotes = classified.get("evidence_quotes") or []

                # Confidence is the max of keyword score (+0.2 prior) and the
                # LLM-assigned impact magnitude. Drop weak candidates.
                confidence = min(
                    1.0,
                    max(round(summary["score"] + 0.2, 4), round(impact, 4)),
                )
                strong_keyword_evidence = (
                    summary["matches"] >= 4 and len(evidence_quotes) >= MIN_EVIDENCE_QUOTES
                )
                if confidence < MIN_CONFIDENCE and not strong_keyword_evidence:
                    continue
                if len(evidence_quotes) < MIN_EVIDENCE_QUOTES and not strong_keyword_evidence:
                    continue

                # Cross-validation: is this exposure non-obvious?
                is_asymmetric = _call_asymmetric_validator(company, theme, classified)
                if is_asymmetric:
                    asymmetric += 1

                # Upsert by (company_id, theme_name) — relies on the unique index
                # added in alembic migration b7c2e1d34a01.
                existing_theme = (
                    db.query(CompanyTheme)
                    .filter(
                        CompanyTheme.company_id == company.id,
                        CompanyTheme.theme_name == theme["code"],
                    )
                    .first()
                )
                payload = {
                    "exposure_type": classified["exposure"],
                    "confidence_score": Decimal(str(confidence)),
                    "impact_score": Decimal(str(round(impact, 4))),
                    "impact_direction": classified.get("impact_direction") or "+",
                    "impact_horizon": classified.get("impact_horizon") or "medium",
                    "is_asymmetric": is_asymmetric,
                    "evidence_quotes": evidence_quotes,
                    "reasoning": (classified.get("reasoning") or "")[:1500],
                    "detected_at": datetime.utcnow(),
                    "validated_by": "theme_tagging_agent",
                    "is_active": True,
                    "updated_at": datetime.utcnow(),
                }
                if existing_theme is None:
                    db.add(
                        CompanyTheme(
                            company_id=company.id,
                            theme_name=theme["code"],
                            **payload,
                        )
                    )
                else:
                    for k, v in payload.items():
                        setattr(existing_theme, k, v)

                edge_subject = ("company", str(company.id))
                edge_object = ("theme", theme["code"])
                existing_edge = (
                    db.query(RelationEdge)
                    .filter(
                        RelationEdge.subject_type == edge_subject[0],
                        RelationEdge.subject_id == edge_subject[1],
                        RelationEdge.predicate == "exposed_to_theme",
                        RelationEdge.object_type == edge_object[0],
                        RelationEdge.object_id == edge_object[1],
                    )
                    .first()
                )
                edge_meta = {
                    "exposure_type": classified["exposure"],
                    "is_asymmetric": is_asymmetric,
                    "impact_direction": classified.get("impact_direction"),
                }
                if existing_edge is None:
                    db.add(
                        RelationEdge(
                            subject_type=edge_subject[0],
                            subject_id=edge_subject[1],
                            predicate="exposed_to_theme",
                            object_type=edge_object[0],
                            object_id=edge_object[1],
                            weight=Decimal(str(round(impact, 4))),
                            source="theme_tagging_agent",
                            valid_from=datetime.utcnow(),
                            metadata_=edge_meta,
                        )
                    )
                else:
                    existing_edge.weight = Decimal(str(round(impact, 4)))
                    existing_edge.valid_from = datetime.utcnow()
                    existing_edge.metadata_ = edge_meta

                applied += 1
                applied_codes.add(theme["code"])

            # Deactivate prior agent-assigned themes that we did NOT re-apply
            # this run, so stale tags drop off.
            if applied_codes:
                (
                    db.query(CompanyTheme)
                    .filter(
                        CompanyTheme.company_id == company.id,
                        CompanyTheme.validated_by == "theme_tagging_agent",
                        ~CompanyTheme.theme_name.in_(applied_codes),
                    )
                    .update({"is_active": False}, synchronize_session=False)
                )

            # Update denormalised company-level summary cache for fast reads.
            company.thematic_exposure_summary = self._build_summary_cache(
                db, company.id
            )

            db.commit()
            return {
                "company_id": str(company_id),
                "themes": applied,
                "asymmetric": asymmetric,
                "status": "ok",
            }
        except Exception:
            db.rollback()
            raise
        finally:
            if own:
                db.close()

    def _build_summary_cache(self, db: Session, company_id: UUID) -> Dict[str, Any]:
        """Compact, denormalised view of a company's active themes.

        Persisted on ``companies.thematic_exposure_summary`` so APIs and the
        Discovery subagent can read it without joining ``company_themes``.
        """
        rows = (
            db.query(CompanyTheme)
            .filter(
                CompanyTheme.company_id == company_id,
                CompanyTheme.is_active.is_(True),
            )
            .order_by(CompanyTheme.confidence_score.desc().nullslast())
            .limit(20)
            .all()
        )
        return {
            "themes": [
                {
                    "code": r.theme_name,
                    "exposure": r.exposure_type,
                    "confidence": float(r.confidence_score or 0.0),
                    "impact": float(r.impact_score or 0.0),
                    "direction": r.impact_direction,
                    "horizon": r.impact_horizon,
                    "is_asymmetric": bool(r.is_asymmetric),
                }
                for r in rows
            ],
            "asymmetric_count": sum(1 for r in rows if r.is_asymmetric),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def tag_universe(self, *, limit: int = 200) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            companies = (
                db.query(Company.id)
                .filter(Company.listing_status == "active")
                .limit(limit)
                .all()
            )
            company_ids = [c.id for c in companies]
        finally:
            db.close()

        totals = {
            "companies": len(company_ids),
            "themes_applied": 0,
            "asymmetric_total": 0,
        }
        for cid in company_ids:
            try:
                res = self.tag_company(cid)
                totals["themes_applied"] += res.get("themes", 0)
                totals["asymmetric_total"] += res.get("asymmetric", 0)
            except Exception as exc:
                logger.warning("theme tag failed for %s: %s", cid, exc)
        return totals
