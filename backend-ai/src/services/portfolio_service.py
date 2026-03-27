"""Portfolio data service."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models import Holding, Portfolio, User


class PortfolioService:
    """Service for portfolio and holdings data."""

    def __init__(self, db: Session):
        self.db = db

    def get_primary_portfolio(self, user_id: UUID) -> Optional[UUID]:
        """Get user's primary portfolio ID."""
        portfolio = (
            self.db.query(Portfolio)
            .filter(Portfolio.user_id == user_id, Portfolio.is_primary == True)
            .first()
        )
        if portfolio:
            return portfolio.id
        # Fallback to first portfolio
        portfolio = (
            self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
        )
        return portfolio.id if portfolio else None

    def get_holdings(self, portfolio_id: UUID) -> List[Dict[str, Any]]:
        """Get current holdings in a portfolio."""
        holdings = (
            self.db.query(Holding)
            .filter(Holding.portfolio_id == portfolio_id)
            .all()
        )
        result = []
        for h in holdings:
            result.append(
                {
                    "holding_id": str(h.id),
                    "company_id": str(h.company_id),
                    "quantity": float(h.quantity),
                    "average_price": float(h.average_price) if h.average_price else None,
                    "current_price": float(h.current_price) if h.current_price else None,
                    "currency": h.currency,
                    "value": (
                        float(h.quantity * (h.current_price or h.average_price or 0))
                        if h.quantity
                        else 0
                    ),
                }
            )
        return result

    def calculate_metrics(self, portfolio_id: UUID) -> Dict[str, Any]:
        """Calculate portfolio-level metrics."""
        holdings = self.get_holdings(portfolio_id)
        if not holdings:
            return {
                "portfolio_id": str(portfolio_id),
                "total_value_inr": 0,
                "holdings_count": 0,
                "top_holding_pct": 0,
                "sector_allocation": {},
                "message": "No holdings in portfolio",
            }

        total_value = sum(h.get("value", 0) or 0 for h in holdings)
        holdings_count = len(holdings)

        top_value = max((h.get("value", 0) or 0 for h in holdings), default=0)
        top_holding_pct = (
            (top_value / total_value) if total_value > 0 else 0
        )

        return {
            "portfolio_id": str(portfolio_id),
            "total_value_inr": total_value,
            "holdings_count": holdings_count,
            "top_holding_pct": round(top_holding_pct, 4),
            "sector_allocation": {},  # Would need company sector lookup
            "holdings": holdings,
        }
