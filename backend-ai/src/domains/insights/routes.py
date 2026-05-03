"""Insight Discovery API routes."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.domains.insights.service import InsightsService

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/insights")
def list_insights(
    insight_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    theme: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return the active insight feed."""
    return InsightsService(db).list_active_insights(
        insight_type=insight_type,
        sector=sector,
        theme=theme,
        limit=limit,
        offset=offset,
        days=days,
    )


@router.get("/insights/metrics")
def insight_metrics(
    lookback_days: int = Query(30, ge=7, le=180),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return per-insight-type precision metrics over a rolling window."""
    return InsightsService(db).metrics(lookback_days=lookback_days)


@router.get("/insights/{insight_id}")
def get_insight(
    insight_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return a single insight card with full evidence."""
    out = InsightsService(db).get(insight_id)
    if not out:
        raise HTTPException(status_code=404, detail="insight_not_found")
    return out
