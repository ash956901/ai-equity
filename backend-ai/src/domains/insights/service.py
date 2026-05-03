"""Insight Discovery service."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.agents.etl_agents.revalidation_agent import precision_by_type
from src.db.models import Insight, InsightEvidence


class InsightsService:
    """Read-side service for the discovery feed."""

    def __init__(self, db: Session):
        self.db = db

    def list_active_insights(
        self,
        *,
        insight_type: Optional[str] = None,
        sector: Optional[str] = None,
        theme: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        days: int = 7,
    ) -> Dict[str, Any]:
        since = datetime.utcnow() - timedelta(days=days)
        query = (
            self.db.query(Insight)
            .filter(Insight.status == "active")
            .filter(Insight.generated_at >= since)
        )
        if insight_type:
            query = query.filter(Insight.insight_type == insight_type)
        if sector:
            query = query.filter(Insight.related_sectors.any(sector))
        if theme:
            query = query.filter(Insight.related_themes.any(theme))
        total = query.count()
        rows = (
            query.order_by(desc(Insight.confidence), desc(Insight.generated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [self._serialize(r) for r in rows],
        }

    def get(self, insight_id: UUID) -> Optional[Dict[str, Any]]:
        row = self.db.query(Insight).filter(Insight.id == insight_id).first()
        if not row:
            return None
        evidence_rows = (
            self.db.query(InsightEvidence)
            .filter(InsightEvidence.insight_id == row.id)
            .all()
        )
        out = self._serialize(row, include_full=True)
        out["evidence_records"] = [
            {
                "source_type": e.source_type,
                "source_id": e.source_id,
                "snippet": e.snippet,
                "weight": float(e.weight) if e.weight is not None else None,
                "metadata": e.metadata_ or {},
            }
            for e in evidence_rows
        ]
        return out

    def metrics(self, *, lookback_days: int = 30) -> Dict[str, Any]:
        return {
            "lookback_days": lookback_days,
            "precision_by_type": precision_by_type(lookback_days=lookback_days),
        }

    def _serialize(self, row: Insight, *, include_full: bool = False) -> Dict[str, Any]:
        base = {
            "insight_id": str(row.id),
            "insight_type": row.insight_type,
            "headline": row.headline,
            "narrative": row.narrative,
            "predicted_direction": row.predicted_direction,
            "horizon_days": row.horizon_days,
            "primary_companies": row.primary_companies or [],
            "related_themes": row.related_themes or [],
            "related_sectors": row.related_sectors or [],
            "confidence": float(row.confidence) if row.confidence is not None else None,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
            "valid_until": row.valid_until.isoformat() if row.valid_until else None,
            "status": row.status,
        }
        if include_full:
            base.update(
                {
                    "evidence_links": row.evidence_links or [],
                    "counter_evidence": row.counter_evidence or [],
                    "confidence_components": row.confidence_components or {},
                    "related_policies": row.related_policies or [],
                }
            )
        return base
