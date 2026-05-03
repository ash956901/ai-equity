"""Event extraction agent.

Walks recent filings + news + transcripts and emits structured ``Event`` rows
for: ``capex, guidance, regulation, mou, leadership_change, supply_disruption,
investor_meet, results, dividend, policy``.

The agent is rule-first - heuristic regexes detect candidate events, then
(optionally) the LLM tightens the structured payload. This keeps the cost of
nightly runs predictable and lets us run without an LLM key.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import (
    Company,
    Event,
    Filing,
    FilingPage,
    NewsArticle,
    Policy,
    RelationEdge,
    Transcript,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


EVENT_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("capex", re.compile(r"\b(capex|capital expenditure|capacity expansion|greenfield|brownfield)\b", re.I)),
    ("guidance", re.compile(r"\b(guidance|outlook|forecast|expect(?:ed|s)? (?:to|that)|target margin)\b", re.I)),
    ("regulation", re.compile(r"\b(sebi|rbi|regulator|investigation|fined|notice|moratorium)\b", re.I)),
    ("mou", re.compile(r"\b(mou|memorandum of understanding|joint venture|jv with|partnership with)\b", re.I)),
    ("leadership_change", re.compile(r"\b(appoint(?:ed|s|ment)|resign(?:ed|s|ation)|step down|new (?:ceo|cfo|chairman|md))\b", re.I)),
    ("supply_disruption", re.compile(r"\b(supply (?:chain|disruption)|raw material shortage|plant shutdown|strike|fire at plant|halt production)\b", re.I)),
    ("investor_meet", re.compile(r"\b(investor (?:day|meet|conference)|analyst meet|conference call|earnings call)\b", re.I)),
    ("results", re.compile(r"\b(quarterly results|q[1-4]\s*results|annual report|results announcement)\b", re.I)),
    ("dividend", re.compile(r"\b(interim dividend|final dividend|special dividend|buyback)\b", re.I)),
    ("policy", re.compile(r"\b(government (?:scheme|policy|notification)|cabinet approval|union budget|gazette)\b", re.I)),
]


def _classify_text(text: str) -> List[str]:
    if not text:
        return []
    matches: List[str] = []
    for label, pat in EVENT_PATTERNS:
        if pat.search(text):
            matches.append(label)
    return matches


def _build_evidence(source_type: str, source_id: str, snippet: str, source_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "source_name": source_name,
        "snippet": (snippet or "")[:600],
    }


def _extract_amount(text: str) -> Optional[float]:
    match = re.search(r"₹\s*(\d+(?:[.,]\d+)?)\s*(crore|cr|lakh|million|billion|bn)?", text or "", re.I)
    if not match:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (match.group(2) or "").lower()
    if "cr" in unit:
        return amount * 1.0
    if "lakh" in unit:
        return amount * 0.01
    if "billion" in unit or unit == "bn":
        return amount * 100.0
    if "million" in unit:
        return amount * 0.1
    return amount


class EventExtractionAgent:
    """Detect structured events from recent filings/news/transcripts."""

    def __init__(self, *, lookback_days: int = 14):
        self.lookback_days = lookback_days

    def run(
        self,
        *,
        db: Optional[Session] = None,
        company_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        own = db is None
        db = db or SessionLocal()
        summary = {"events_created": 0, "policies_created": 0, "edges_created": 0}
        try:
            since = datetime.utcnow() - timedelta(days=self.lookback_days)

            # 1. Filings (use FilingPage so we keep page provenance)
            filings_query = (
                db.query(FilingPage, Filing)
                .join(Filing, FilingPage.filing_id == Filing.id)
                .filter(Filing.created_at >= since)
                .filter(Filing.status.in_(["parsed", "embedded"]))
            )
            if company_id:
                filings_query = filings_query.filter(Filing.company_id == company_id)
            for page, filing in filings_query.limit(500).all():
                if not page.text:
                    continue
                events = _classify_text(page.text)
                for ev_type in events:
                    self._upsert_event(
                        db,
                        company_id=filing.company_id,
                        event_type=ev_type,
                        event_date=filing.filing_date or date.today(),
                        headline=filing.title,
                        snippet=page.text[:1200],
                        source_filing_id=filing.id,
                        summary=summary,
                    )

            # 2. News
            news_query = db.query(NewsArticle).filter(NewsArticle.published_at >= since)
            if company_id:
                news_query = news_query.filter(NewsArticle.company_id == company_id)
            for n in news_query.limit(500).all():
                text = (n.headline or "") + ". " + (n.body or "")
                events = _classify_text(text)
                for ev_type in events:
                    self._upsert_event(
                        db,
                        company_id=n.company_id,
                        event_type=ev_type,
                        event_date=(n.published_at or datetime.utcnow()).date(),
                        headline=n.headline,
                        snippet=text[:1200],
                        source_news_id=n.id,
                        summary=summary,
                    )

            # 3. Transcripts
            tx_query = (
                db.query(TranscriptSegment, Transcript)
                .join(Transcript, TranscriptSegment.transcript_id == Transcript.id)
                .filter(Transcript.created_at >= since)
            )
            if company_id:
                tx_query = tx_query.filter(Transcript.company_id == company_id)
            for seg, tx in tx_query.limit(800).all():
                events = _classify_text(seg.text or "")
                for ev_type in events:
                    self._upsert_event(
                        db,
                        company_id=tx.company_id,
                        event_type=ev_type,
                        event_date=tx.period_end or date.today(),
                        headline=tx.title or "Concall mention",
                        snippet=(seg.text or "")[:1200],
                        source_transcript_id=tx.id,
                        speaker_role=seg.speaker_role,
                        summary=summary,
                    )

            db.commit()
            return summary
        except Exception:
            db.rollback()
            raise
        finally:
            if own:
                db.close()

    # ------------------------------------------------------------------ #
    #  helpers                                                           #
    # ------------------------------------------------------------------ #

    def _upsert_event(
        self,
        db: Session,
        *,
        company_id: Optional[UUID],
        event_type: str,
        event_date,
        headline: Optional[str],
        snippet: str,
        source_filing_id: Optional[UUID] = None,
        source_news_id: Optional[UUID] = None,
        source_transcript_id: Optional[UUID] = None,
        speaker_role: Optional[str] = None,
        summary: Optional[Dict[str, int]] = None,
    ) -> None:
        # Cheap dedup: same company/type/date/source -> already extracted
        existing = (
            db.query(Event)
            .filter(
                Event.event_type == event_type,
                Event.event_date == event_date,
                Event.company_id == company_id,
                (Event.source_filing_id == source_filing_id)
                | (Event.source_news_id == source_news_id)
                | (Event.source_transcript_id == source_transcript_id),
            )
            .first()
        )
        if existing:
            return

        amount_cr = _extract_amount(snippet)
        evidence = []
        if source_filing_id:
            evidence.append(_build_evidence("filing", str(source_filing_id), snippet))
        if source_news_id:
            evidence.append(_build_evidence("news", str(source_news_id), snippet))
        if source_transcript_id:
            evidence.append(_build_evidence("transcript", str(source_transcript_id), snippet))

        ev = Event(
            company_id=company_id,
            event_type=event_type,
            event_date=event_date,
            headline=(headline or event_type)[:500],
            structured_data={
                "amount_cr": amount_cr,
                "speaker_role": speaker_role,
                "snippet": snippet[:600],
            },
            confidence=Decimal("0.55"),
            sentiment_label=None,
            source_filing_id=source_filing_id,
            source_news_id=source_news_id,
            source_transcript_id=source_transcript_id,
            evidence_links=evidence,
            is_active=True,
        )
        db.add(ev)
        if summary is not None:
            summary["events_created"] += 1

        # Policy entity for "policy" events
        if event_type == "policy":
            self._upsert_policy(db, headline=headline, summary=snippet, summary_counters=summary)

        # Relation edge: company -> triggered_event
        if company_id:
            edge_exists = (
                db.query(RelationEdge)
                .filter(
                    RelationEdge.subject_type == "company",
                    RelationEdge.subject_id == str(company_id),
                    RelationEdge.predicate == "triggered_event",
                    RelationEdge.object_type == "event",
                    RelationEdge.object_id == event_type,
                )
                .first()
            )
            if not edge_exists:
                db.add(
                    RelationEdge(
                        subject_type="company",
                        subject_id=str(company_id),
                        predicate="triggered_event",
                        object_type="event",
                        object_id=event_type,
                        weight=Decimal("0.5"),
                        source="event_extraction_agent",
                        valid_from=datetime.utcnow(),
                    )
                )
                if summary is not None:
                    summary["edges_created"] += 1

    def _upsert_policy(
        self,
        db: Session,
        *,
        headline: Optional[str],
        summary: str,
        summary_counters: Optional[Dict[str, int]] = None,
    ) -> None:
        if not headline:
            return
        code = re.sub(r"[^a-z0-9]+", "_", headline.lower())[:80].strip("_")
        if not code:
            return
        existing = db.query(Policy).filter(Policy.code == code).first()
        if existing:
            return
        db.add(
            Policy(
                code=code,
                name=headline[:255],
                summary=summary[:1500],
                source_url=None,
                effective_date=None,
            )
        )
        if summary_counters is not None:
            summary_counters["policies_created"] += 1
