"""Portfolio API routes."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Company, Holding, Portfolio, User
from src.services.portfolio_service import PortfolioService
from src.utils.data_sources import portfolio_sources

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


class CreatePortfolioRequest(BaseModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_primary: bool = False


class AddHoldingRequest(BaseModel):
    company_id: UUID
    quantity: float = Field(..., gt=0)
    average_price: Optional[float] = None


@router.get("/")
def list_portfolios(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List portfolios for a user."""
    portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id)
        .order_by(Portfolio.is_primary.desc(), Portfolio.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "broker": p.broker,
            "is_primary": p.is_primary,
            "created_at": p.created_at.isoformat(),
        }
        for p in portfolios
    ]


@router.post("/", status_code=201)
def create_portfolio(
    request: CreatePortfolioRequest,
    db: Session = Depends(get_db),
):
    """Create a portfolio."""
    portfolio = Portfolio(
        user_id=request.user_id,
        name=request.name,
        description=request.description,
        is_primary=request.is_primary,
    )
    db.add(portfolio)
    if request.is_primary:
        db.query(Portfolio).filter(
            Portfolio.user_id == request.user_id,
            Portfolio.id != portfolio.id,
        ).update({"is_primary": False})
    db.commit()
    db.refresh(portfolio)
    return {"id": str(portfolio.id), "name": portfolio.name}


@router.get("/{portfolio_id}")
def get_portfolio(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get portfolio with holdings."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    svc = PortfolioService(db)
    holdings = svc.get_holdings(portfolio_id)
    metrics = svc.calculate_metrics(portfolio_id)

    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "description": portfolio.description,
        "broker": portfolio.broker,
        "is_primary": portfolio.is_primary,
        "holdings": holdings,
        "metrics": metrics,
        "data_sources": portfolio_sources(portfolio.broker),
    }


@router.post("/{portfolio_id}/holdings", status_code=201)
def add_holding(
    portfolio_id: UUID,
    request: AddHoldingRequest,
    db: Session = Depends(get_db),
):
    """Add or update holding in portfolio."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    company = db.query(Company).filter(Company.id == request.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    existing = (
        db.query(Holding)
        .filter(
            Holding.portfolio_id == portfolio_id,
            Holding.company_id == request.company_id,
        )
        .first()
    )

    from decimal import Decimal

    if existing:
        existing.quantity += Decimal(str(request.quantity))
        if request.average_price:
            existing.average_price = Decimal(str(request.average_price))
        db.commit()
        return {"holding_id": str(existing.id), "action": "updated"}
    else:
        holding = Holding(
            portfolio_id=portfolio_id,
            company_id=request.company_id,
            quantity=Decimal(str(request.quantity)),
            average_price=Decimal(str(request.average_price)) if request.average_price else None,
        )
        db.add(holding)
        db.commit()
        db.refresh(holding)
        return {"holding_id": str(holding.id), "action": "created"}
