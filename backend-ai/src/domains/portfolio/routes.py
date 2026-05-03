"""Portfolio API routes."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
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


@router.get("/")
def list_portfolios(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List portfolios for a user."""
    service = PortfoliosService(db)
    return service.list_portfolios(user_id)


@router.post("/", status_code=201)
def create_portfolio(
    request: CreatePortfolioRequest,
    db: Session = Depends(get_db),
):
    """Create a portfolio."""
    service = PortfoliosService(db)
    return service.create_portfolio(
        user_id=request.user_id,
        name=request.name,
        description=request.description,
        is_primary=request.is_primary,
    )


@router.get("/suggestions")
def get_ai_suggestions(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get AI-generated investment suggestions for the user's primary portfolio."""
    service = PortfoliosService(db)
    return service.get_ai_suggestions(user_id)


@router.get("/{portfolio_id}")
def get_portfolio(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get portfolio with holdings and basic metrics."""
    service = PortfoliosService(db)
    return service.get_portfolio(portfolio_id)


@router.get("/{portfolio_id}/metrics")
def get_portfolio_metrics(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get quantitative risk metrics for a portfolio.

    Returns Beta, Sharpe Ratio, Volatility, Diversification Score,
    and Sector Allocation breakdown computed from current holdings.
    """
    service = PortfoliosService(db)
    return service.get_metrics(portfolio_id)




@router.post("/{portfolio_id}/holdings", status_code=201)

def add_holding(
    portfolio_id: UUID,
    request: AddHoldingRequest,
    db: Session = Depends(get_db),
):
    """Add or update holding in portfolio."""
    service = PortfoliosService(db)
    return service.add_holding(
        portfolio_id=portfolio_id,
        company_id=request.company_id,
        quantity=request.quantity,
        average_price=request.average_price,
    )
