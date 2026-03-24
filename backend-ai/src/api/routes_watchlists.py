"""Watchlist API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Company, WatchlistModel, WatchlistCompany

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


class CreateWatchlistRequest(BaseModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=255)


class AddCompanyRequest(BaseModel):
    company_id: UUID


@router.get("/")
def list_watchlists(user_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """List watchlists for a user."""
    watchlists = (
        db.query(WatchlistModel)
        .filter(WatchlistModel.user_id == user_id)
        .order_by(WatchlistModel.created_at.desc())
        .all()
    )
    result = []
    for w in watchlists:
        companies = (
            db.query(WatchlistCompany)
            .filter(WatchlistCompany.watchlist_id == w.id)
            .all()
        )
        result.append({
            "id": str(w.id),
            "user_id": str(w.user_id),
            "name": w.name,
            "companies": [str(c.company_id) for c in companies],
            "created_at": w.created_at.isoformat(),
        })
    return result


@router.post("/", status_code=201)
def create_watchlist(request: CreateWatchlistRequest, db: Session = Depends(get_db)):
    """Create a new watchlist."""
    watchlist = WatchlistModel(user_id=request.user_id, name=request.name)
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    return {
        "id": str(watchlist.id),
        "user_id": str(watchlist.user_id),
        "name": watchlist.name,
        "companies": [],
        "created_at": watchlist.created_at.isoformat(),
    }


@router.post("/{watchlist_id}/companies", status_code=201)
def add_company(watchlist_id: UUID, request: AddCompanyRequest, db: Session = Depends(get_db)):
    """Add a company to a watchlist."""
    watchlist = db.query(WatchlistModel).filter(WatchlistModel.id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    company = db.query(Company).filter(Company.id == request.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    existing = (
        db.query(WatchlistCompany)
        .filter(WatchlistCompany.watchlist_id == watchlist_id, WatchlistCompany.company_id == request.company_id)
        .first()
    )
    if existing:
        return {"status": "already_added"}

    wc = WatchlistCompany(watchlist_id=watchlist_id, company_id=request.company_id)
    db.add(wc)
    db.commit()
    return {"status": "added", "company_id": str(request.company_id)}


@router.delete("/{watchlist_id}/companies/{company_id}", status_code=204)
def remove_company(watchlist_id: UUID, company_id: UUID, db: Session = Depends(get_db)):
    """Remove a company from a watchlist."""
    wc = (
        db.query(WatchlistCompany)
        .filter(WatchlistCompany.watchlist_id == watchlist_id, WatchlistCompany.company_id == company_id)
        .first()
    )
    if not wc:
        raise HTTPException(status_code=404, detail="Company not in watchlist")
    db.delete(wc)
    db.commit()
