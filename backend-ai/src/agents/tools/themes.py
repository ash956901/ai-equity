"""Tools for theme exploration and tagging."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from sqlalchemy import desc

from src.agents.tools._utils import emit_tool_metric, resolve_company_id
from src.db.database import get_db
from src.db.models import Company, CompanyTheme


def _serialize_theme(t: CompanyTheme) -> Dict[str, Any]:
    return {
        "theme": t.theme_name,
        "exposure_type": t.exposure_type,
        "impact_score": float(t.impact_score) if t.impact_score is not None else None,
        "impact_direction": t.impact_direction,
        "impact_horizon": t.impact_horizon,
        "confidence_score": (
            float(t.confidence_score) if t.confidence_score is not None else None
        ),
        "is_asymmetric": bool(t.is_asymmetric),
        "evidence_quotes": (t.evidence_quotes or [])[:3],
        "reasoning": (t.reasoning or "")[:500],
        "detected_at": t.detected_at.isoformat() if t.detected_at else None,
    }


@tool
def search_themes(
    query: str,
    min_impact: float = 0.3,
    asymmetric_only: bool = False,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Find companies tagged with a given theme.

    Args:
        query: Theme name or keyword (e.g. "ethanol_blending", "AI Data Centres").
        min_impact: Minimum impact_score (0-1).
        asymmetric_only: If True, return only non-obvious / second-order
            exposures (Castrol-style insights). Use for the Discovery feed.
        limit: Max companies to return.
    """
    emit_tool_metric("search_themes")
    db = next(get_db())
    try:
        q = (
            db.query(CompanyTheme, Company)
            .join(Company, CompanyTheme.company_id == Company.id)
            .filter(CompanyTheme.is_active.is_(True))
            .filter(
                (CompanyTheme.theme_name.ilike(f"%{query}%"))
                | (CompanyTheme.reasoning.ilike(f"%{query}%"))
            )
            .filter(CompanyTheme.impact_score >= min_impact)
        )
        if asymmetric_only:
            q = q.filter(CompanyTheme.is_asymmetric.is_(True))
        rows = q.order_by(desc(CompanyTheme.impact_score)).limit(limit).all()
        return [
            {
                "company_id": str(c.id),
                "company_name": c.name,
                "ticker_nse": c.ticker_nse,
                "sector": c.sector,
                "industry": c.industry,
                **_serialize_theme(t),
            }
            for t, c in rows
        ]
    finally:
        db.close()


@tool
def get_company_themes(
    company_id: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Return all active themes tagged for a company, ordered by impact.

    Output rows include ``is_asymmetric`` so the Discovery / company
    analysis subagent can highlight Castrol-style hidden exposures
    separately from the primary classification.

    Args:
        company_id: Company UUID or name/ticker.
        limit: Max themes to return.
    """
    emit_tool_metric("get_company_themes")
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return [{"error": str(e)}]
        rows = (
            db.query(CompanyTheme)
            .filter(CompanyTheme.company_id == uid)
            .filter(CompanyTheme.is_active.is_(True))
            .order_by(desc(CompanyTheme.impact_score))
            .limit(limit)
            .all()
        )
        return [_serialize_theme(r) for r in rows]
    finally:
        db.close()


@tool
def get_asymmetric_company_themes(
    company_id: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Return only the *non-obvious* (asymmetric) themes for a company.

    Use this when the user asks "what hidden exposures does X have?" or
    when surfacing the headline insight on a company page.
    """
    emit_tool_metric("get_asymmetric_company_themes")
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return [{"error": str(e)}]
        rows = (
            db.query(CompanyTheme)
            .filter(CompanyTheme.company_id == uid)
            .filter(CompanyTheme.is_active.is_(True))
            .filter(CompanyTheme.is_asymmetric.is_(True))
            .order_by(desc(CompanyTheme.impact_score))
            .limit(limit)
            .all()
        )
        return [_serialize_theme(r) for r in rows]
    finally:
        db.close()
