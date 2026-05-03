"""Tools for the events table."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from sqlalchemy import desc

from src.agents.tools._utils import resolve_company_id
from src.db.database import get_db
from src.db.models import Company, Event


@tool
def search_events(
    event_type: Optional[str] = None,
    company_id: Optional[str] = None,
    days: int = 14,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Search structured events extracted from filings/news/transcripts.

    Args:
        event_type: Optional filter (capex, guidance, regulation, mou,
            leadership_change, supply_disruption, investor_meet, results,
            dividend, policy).
        company_id: Optional company UUID or name/ticker filter.
        days: Look-back window.
        limit: Max events to return.
    """
    db = next(get_db())
    try:
        cutoff = date.today() - timedelta(days=days)
        query = db.query(Event, Company).outerjoin(Company, Event.company_id == Company.id)
        query = query.filter(Event.is_active.is_(True))
        if event_type:
            query = query.filter(Event.event_type == event_type)
        if company_id:
            try:
                uid = resolve_company_id(company_id, db)
            except ValueError as e:
                return [{"error": str(e)}]
            query = query.filter(Event.company_id == uid)
        query = query.filter(Event.event_date >= cutoff).order_by(desc(Event.event_date)).limit(limit)
        rows = query.all()
        return [
            {
                "event_id": str(ev.id),
                "company_id": str(ev.company_id) if ev.company_id else None,
                "company_name": c.name if c else None,
                "ticker": (c.ticker_nse or c.ticker_bse) if c else None,
                "event_type": ev.event_type,
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "headline": ev.headline,
                "structured": ev.structured_data or {},
                "evidence": (ev.evidence_links or [])[:3],
                "confidence": float(ev.confidence) if ev.confidence is not None else None,
            }
            for ev, c in rows
        ]
    finally:
        db.close()
