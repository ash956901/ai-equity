"""Screening and discovery API routes."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User
from src.domains.auth.dependencies import assert_self, get_current_user, optional_user
from src.domains.screens.service import ScreensService

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
    themes: Optional[list[str]] = Field(
        default=None,
        description="Theme codes; matched companies must have at least one active tag",
    )
    min_theme_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    asymmetric_only: bool = False
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None
    min_roe: Optional[float] = None
    max_debt_to_equity: Optional[float] = None
    limit: int = Field(default=50, le=200)


@router.get("/")
def list_screens(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List saved screens for a user."""
    assert_self(user_id, current_user)
    service = ScreensService(db)
    return service.list_screens(user_id)


@router.post("/", status_code=201)
def save_screen(
    request: SaveScreenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a screen filter configuration."""
    assert_self(request.user_id, current_user)
    service = ScreensService(db)
    return service.save_screen(
        user_id=request.user_id,
        name=request.name,
        filters=request.filters,
    )


@router.post("/run")
def run_screen(
    request: RunScreenRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Execute a screen query against the companies database."""
    service = ScreensService(db)
    return service.run_screen(
        sector=request.sector,
        industry=request.industry,
        min_market_cap=request.min_market_cap,
        max_market_cap=request.max_market_cap,
        themes=request.themes,
        min_theme_confidence=request.min_theme_confidence,
        asymmetric_only=request.asymmetric_only,
        min_pe=request.min_pe,
        max_pe=request.max_pe,
        min_roe=request.min_roe,
        max_debt_to_equity=request.max_debt_to_equity,
        limit=request.limit,
    )
