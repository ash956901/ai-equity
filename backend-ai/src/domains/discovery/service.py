"""Discovery service: read-side queries over `company_themes`,
`theme_taxonomy`, and `relation_edges`. The heavy LLM tagging happens
offline in `src.agents.etl_agents.theme_agent.ThemeTaggingAgent` —
this service stays cheap and synchronous.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Integer, desc, func
from sqlalchemy.orm import Session

from src.db.models import (
    Company,
    CompanyTheme,
    RelationEdge,
    ThemeTaxonomy,
)


def _serialize_theme(t: CompanyTheme, c: Optional[Company] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "theme_code": t.theme_name,
        "exposure_type": t.exposure_type,
        "impact_score": float(t.impact_score) if t.impact_score is not None else None,
        "impact_direction": t.impact_direction,
        "impact_horizon": t.impact_horizon,
        "confidence_score": (
            float(t.confidence_score) if t.confidence_score is not None else None
        ),
        "is_asymmetric": bool(t.is_asymmetric),
        "evidence_quotes": (t.evidence_quotes or [])[:3],
        "reasoning": (t.reasoning or "")[:400],
        "detected_at": t.detected_at.isoformat() if t.detected_at else None,
    }
    if c is not None:
        payload.update(
            {
                "company_id": str(c.id),
                "company_name": c.name,
                "ticker_nse": c.ticker_nse,
                "sector": c.sector,
                "industry": c.industry,
            }
        )
    return payload


class DiscoveryService:
    """Read-side queries powering the Discovery feed and theme pages."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    #  Theme catalogue
    # ------------------------------------------------------------------

    def list_themes(self, *, only_with_companies: bool = False) -> list[dict[str, Any]]:
        """List the theme taxonomy with rolled-up company / asymmetric counts."""
        agg = (
            self.db.query(
                CompanyTheme.theme_name,
                func.count(CompanyTheme.id).label("company_count"),
                func.sum(
                    func.cast(CompanyTheme.is_asymmetric, Integer)
                ).label("asymmetric_count"),
            )
            .filter(CompanyTheme.is_active.is_(True))
            .group_by(CompanyTheme.theme_name)
            .all()
        )
        counts = {
            row.theme_name: {
                "company_count": int(row.company_count or 0),
                "asymmetric_count": int(row.asymmetric_count or 0),
            }
            for row in agg
        }

        themes = (
            self.db.query(ThemeTaxonomy)
            .filter(ThemeTaxonomy.is_active.is_(True))
            .order_by(ThemeTaxonomy.category, ThemeTaxonomy.label)
            .all()
        )
        out: list[dict[str, Any]] = []
        for t in themes:
            stats = counts.get(t.code, {"company_count": 0, "asymmetric_count": 0})
            if only_with_companies and stats["company_count"] == 0:
                continue
            out.append(
                {
                    "code": t.code,
                    "label": t.label,
                    "category": t.category,
                    "parent_code": t.parent_code,
                    "description": t.description,
                    "keywords": t.keywords or [],
                    **stats,
                }
            )
        return out

    # ------------------------------------------------------------------
    #  Companies in a theme
    # ------------------------------------------------------------------

    def companies_in_theme(
        self,
        theme: str,
        *,
        min_confidence: float = 0.55,
        exposure_types: Optional[list[str]] = None,
        asymmetric_only: bool = False,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        q = (
            self.db.query(CompanyTheme, Company)
            .join(Company, CompanyTheme.company_id == Company.id)
            .filter(CompanyTheme.is_active.is_(True))
            .filter(CompanyTheme.theme_name == theme)
            .filter(CompanyTheme.confidence_score >= Decimal(str(min_confidence)))
        )
        if exposure_types:
            q = q.filter(CompanyTheme.exposure_type.in_(exposure_types))
        if asymmetric_only:
            q = q.filter(CompanyTheme.is_asymmetric.is_(True))
        rows = q.order_by(desc(CompanyTheme.impact_score)).limit(limit).all()
        return [_serialize_theme(t, c) for t, c in rows]

    # ------------------------------------------------------------------
    #  Themes for a company
    # ------------------------------------------------------------------

    def themes_for_company(
        self, company_id: UUID, *, asymmetric_only: bool = False, limit: int = 30
    ) -> list[dict[str, Any]]:
        q = (
            self.db.query(CompanyTheme)
            .filter(CompanyTheme.company_id == company_id)
            .filter(CompanyTheme.is_active.is_(True))
        )
        if asymmetric_only:
            q = q.filter(CompanyTheme.is_asymmetric.is_(True))
        rows = q.order_by(desc(CompanyTheme.impact_score)).limit(limit).all()
        return [_serialize_theme(r) for r in rows]

    # ------------------------------------------------------------------
    #  Asymmetric feed - the "Castrol moments" surfaced platform-wide
    # ------------------------------------------------------------------

    def asymmetric_feed(
        self,
        *,
        theme: Optional[str] = None,
        sector: Optional[str] = None,
        min_confidence: float = 0.6,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        q = (
            self.db.query(CompanyTheme, Company)
            .join(Company, CompanyTheme.company_id == Company.id)
            .filter(CompanyTheme.is_active.is_(True))
            .filter(CompanyTheme.is_asymmetric.is_(True))
            .filter(CompanyTheme.confidence_score >= Decimal(str(min_confidence)))
        )
        if theme:
            q = q.filter(CompanyTheme.theme_name == theme)
        if sector:
            q = q.filter(Company.sector == sector)
        rows = (
            q.order_by(
                desc(CompanyTheme.impact_score),
                desc(CompanyTheme.confidence_score),
            )
            .limit(limit)
            .all()
        )
        return [_serialize_theme(t, c) for t, c in rows]

    # ------------------------------------------------------------------
    #  Theme graph
    # ------------------------------------------------------------------

    def theme_neighbors(self, theme: str) -> list[dict[str, Any]]:
        """Direct outbound theme→theme edges (no multi-hop)."""
        edges = (
            self.db.query(RelationEdge)
            .filter(RelationEdge.subject_type == "theme")
            .filter(RelationEdge.subject_id == theme)
            .filter(RelationEdge.object_type == "theme")
            .all()
        )
        return [
            {
                "predicate": e.predicate,
                "neighbor_code": e.object_id,
                "weight": float(e.weight) if e.weight is not None else None,
                "source": e.source,
            }
            for e in edges
        ]
