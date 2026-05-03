"""Discovery / hidden-insight API routes.

Read-only endpoints that surface the offline theme tagger's output:

- ``GET /discovery/themes`` -- catalogue with company / asymmetric counts.
- ``GET /discovery/themes/{theme}/companies`` -- companies in a theme.
- ``GET /discovery/companies/{company_id}/themes`` -- themes for a company.
- ``GET /discovery/asymmetric`` -- the headline "Castrol-style" feed.
- ``GET /discovery/themes/{theme}/neighbors`` -- direct theme graph edges.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.domains.discovery.service import DiscoveryService

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/themes")
def list_themes(
    only_with_companies: bool = False,
    db: Session = Depends(get_db),
):
    """List all themes in the taxonomy with rolled-up exposure counts."""
    return DiscoveryService(db).list_themes(only_with_companies=only_with_companies)


@router.get("/themes/{theme}/companies")
def companies_in_theme(
    theme: str,
    min_confidence: float = Query(0.55, ge=0.0, le=1.0),
    exposure_type: Optional[str] = Query(
        None,
        description="Comma-separated, e.g. 'direct,derivative,second_order'",
    ),
    asymmetric_only: bool = False,
    limit: int = Query(25, le=200),
    db: Session = Depends(get_db),
):
    """Reverse lookup: which companies are exposed to a given theme?"""
    types_filter = (
        [s.strip() for s in exposure_type.split(",") if s.strip()]
        if exposure_type
        else None
    )
    return DiscoveryService(db).companies_in_theme(
        theme=theme,
        min_confidence=min_confidence,
        exposure_types=types_filter,
        asymmetric_only=asymmetric_only,
        limit=limit,
    )


@router.get("/companies/{company_id}/themes")
def themes_for_company(
    company_id: UUID,
    asymmetric_only: bool = False,
    limit: int = Query(30, le=200),
    db: Session = Depends(get_db),
):
    """All active themes tagged for a company."""
    return DiscoveryService(db).themes_for_company(
        company_id=company_id,
        asymmetric_only=asymmetric_only,
        limit=limit,
    )


@router.get("/asymmetric")
def asymmetric_feed(
    theme: Optional[str] = None,
    sector: Optional[str] = None,
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    limit: int = Query(30, le=200),
    db: Session = Depends(get_db),
):
    """The platform-wide 'Castrol moments' feed -- the killer surface."""
    return DiscoveryService(db).asymmetric_feed(
        theme=theme,
        sector=sector,
        min_confidence=min_confidence,
        limit=limit,
    )


@router.get("/themes/{theme}/neighbors")
def theme_neighbors(theme: str, db: Session = Depends(get_db)):
    """Direct theme→theme edges (one hop)."""
    edges = DiscoveryService(db).theme_neighbors(theme)
    if not edges:
        raise HTTPException(status_code=404, detail="No neighbors found for theme")
    return edges
