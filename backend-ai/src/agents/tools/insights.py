"""Tools for surfacing precomputed insights to the orchestrator."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from sqlalchemy import desc

from src.db.database import get_db
from src.db.models import Insight


@tool
def list_daily_insights(
    insight_type: Optional[str] = None,
    sector: Optional[str] = None,
    theme: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Return today's active insight cards from the discovery feed.

    Args:
        insight_type: Filter to causal_cross_industry, supply_chain_ripple,
            sentiment_driven, event_catalyst, second_order.
        sector: Filter to insights tagged with the given sector.
        theme: Filter to insights tagged with the given theme code.
        limit: Max insights to return.
    """
    db = next(get_db())
    try:
        since = datetime.utcnow() - timedelta(days=2)
        query = (
            db.query(Insight)
            .filter(Insight.status == "active")
            .filter(Insight.generated_at >= since)
        )
        if insight_type:
            query = query.filter(Insight.insight_type == insight_type)
        if sector:
            query = query.filter(Insight.related_sectors.any(sector))
        if theme:
            query = query.filter(Insight.related_themes.any(theme))
        rows = query.order_by(desc(Insight.confidence)).limit(limit).all()
        return [
            {
                "insight_id": str(r.id),
                "insight_type": r.insight_type,
                "headline": r.headline,
                "narrative": r.narrative,
                "predicted_direction": r.predicted_direction,
                "horizon_days": r.horizon_days,
                "primary_companies": r.primary_companies or [],
                "related_themes": r.related_themes or [],
                "related_sectors": r.related_sectors or [],
                "confidence": float(r.confidence) if r.confidence is not None else None,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "evidence": r.evidence_links or [],
            }
            for r in rows
        ]
    finally:
        db.close()


@tool
def get_insight(insight_id: str) -> Dict[str, Any]:
    """Fetch a single insight card with its full evidence + counter-evidence."""
    db = next(get_db())
    try:
        row = db.query(Insight).filter(Insight.id == insight_id).first()
        if not row:
            return {"error": "insight_not_found"}
        return {
            "insight_id": str(row.id),
            "insight_type": row.insight_type,
            "headline": row.headline,
            "narrative": row.narrative,
            "predicted_direction": row.predicted_direction,
            "horizon_days": row.horizon_days,
            "primary_companies": row.primary_companies or [],
            "related_themes": row.related_themes or [],
            "related_sectors": row.related_sectors or [],
            "related_policies": row.related_policies or [],
            "evidence_links": row.evidence_links or [],
            "counter_evidence": row.counter_evidence or [],
            "confidence": float(row.confidence) if row.confidence is not None else None,
            "confidence_components": row.confidence_components or {},
            "status": row.status,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
            "valid_until": row.valid_until.isoformat() if row.valid_until else None,
        }
    finally:
        db.close()
