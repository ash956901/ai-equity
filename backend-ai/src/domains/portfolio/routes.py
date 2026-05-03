"""Portfolio API routes."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Portfolio, User
from src.domains.auth.dependencies import assert_self, get_current_user
from src.domains.portfolio.service import PortfoliosService

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


def _assert_portfolio_owner(
    db: Session, portfolio_id: UUID, current_user: User
) -> Portfolio:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your portfolio")
    return portfolio


@router.get("/me/holdings-count")
def my_holdings_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Total distinct-company holdings count for the logged-in user."""
    from src.db.models import Holding

    rows = (
        db.query(Holding.company_id)
        .join(Portfolio, Portfolio.id == Holding.portfolio_id)
        .filter(Portfolio.user_id == current_user.id)
        .distinct()
        .all()
    )
    return {"count": len(rows)}


@router.get("/")
def list_portfolios(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List portfolios for a user."""
    assert_self(user_id, current_user)
    service = PortfoliosService(db)
    return service.list_portfolios(user_id)


@router.post("/", status_code=201)
def create_portfolio(
    request: CreatePortfolioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a portfolio."""
    assert_self(request.user_id, current_user)
    service = PortfoliosService(db)
    return service.create_portfolio(
        user_id=request.user_id,
        name=request.name,
        description=request.description,
        is_primary=request.is_primary,
    )


@router.get("/{portfolio_id}")
def get_portfolio(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get portfolio with holdings."""
    _assert_portfolio_owner(db, portfolio_id, current_user)
    service = PortfoliosService(db)
    return service.get_portfolio(portfolio_id)


@router.post("/{portfolio_id}/holdings", status_code=201)
def add_holding(
    portfolio_id: UUID,
    request: AddHoldingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add or update holding in portfolio."""
    _assert_portfolio_owner(db, portfolio_id, current_user)
    service = PortfoliosService(db)
    return service.add_holding(
        portfolio_id=portfolio_id,
        company_id=request.company_id,
        quantity=request.quantity,
        average_price=request.average_price,
    )
