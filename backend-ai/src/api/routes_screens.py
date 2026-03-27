"""Screening and discovery API routes."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Company, SavedScreen

router = APIRouter(prefix="/screens", tags=["screens"])


class SaveScreenRequest(BaseModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    filters: dict = Field(default_factory=dict)


class RunScreenRequest(BaseModel):
    sector: Optional[str] = None
    industry: Optional[str] = None
    min_market_cap: Optional[int] = None
    max_market_cap: Optional[int] = None
    limit: int = Field(default=50, le=200)


@router.get("/")
def list_screens(user_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """List saved screens for a user."""
    screens = (
        db.query(SavedScreen)
        .filter(SavedScreen.user_id == user_id)
        .order_by(SavedScreen.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "filters": s.filters or {},
            "created_at": s.created_at.isoformat(),
        }
        for s in screens
    ]


@router.post("/", status_code=201)
def save_screen(request: SaveScreenRequest, db: Session = Depends(get_db)):
    """Save a screen filter configuration."""
    screen = SavedScreen(
        user_id=request.user_id,
        name=request.name,
        filters=request.filters,
    )
    db.add(screen)
    db.commit()
    db.refresh(screen)
    return {"id": str(screen.id), "name": screen.name}


@router.post("/run")
def run_screen(request: RunScreenRequest, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Execute a screen query against the companies database."""
    query = db.query(Company).filter(Company.listing_status == "active")

    if request.sector:
        query = query.filter(Company.sector == request.sector)
    if request.industry:
        query = query.filter(Company.industry == request.industry)
    if request.min_market_cap:
        query = query.filter(Company.market_cap_inr >= request.min_market_cap)
    if request.max_market_cap:
        query = query.filter(Company.market_cap_inr <= request.max_market_cap)

    companies = query.order_by(Company.market_cap_inr.desc().nullslast()).limit(request.limit).all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "ticker_nse": c.ticker_nse,
            "ticker_bse": c.ticker_bse,
            "sector": c.sector,
            "industry": c.industry,
            "market_cap_inr": c.market_cap_inr,
        }
        for c in companies
    ]
