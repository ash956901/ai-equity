"""Business logic for portfolio endpoints."""

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.db.models import Company, Holding, Portfolio
from src.services.portfolio_service import PortfolioService
from src.utils.data_sources import portfolio_sources


class PortfoliosService:
    """Handles portfolio CRUD and holdings operations."""

    def __init__(self, db: Session):
        self.db = db
        self._portfolio_service = PortfolioService(db)

    def list_portfolios(self, user_id: UUID) -> list[dict[str, Any]]:
        portfolios = (
            self.db.query(Portfolio)
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

    def create_portfolio(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str],
        is_primary: bool,
    ) -> dict[str, Any]:
        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            description=description,
            is_primary=is_primary,
        )
        self.db.add(portfolio)
        if is_primary:
            self.db.query(Portfolio).filter(
                Portfolio.user_id == user_id,
                Portfolio.id != portfolio.id,
            ).update({"is_primary": False})
        self.db.commit()
        self.db.refresh(portfolio)
        return {"id": str(portfolio.id), "name": portfolio.name}

    def get_portfolio(self, portfolio_id: UUID) -> dict[str, Any]:
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        holdings = self._portfolio_service.get_holdings(portfolio_id)
        metrics = self._portfolio_service.calculate_metrics(portfolio_id)
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

    def get_metrics(self, portfolio_id: UUID) -> dict[str, Any]:
        """Return only the quantitative risk metrics for a portfolio."""
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        metrics = self._portfolio_service.calculate_metrics(portfolio_id)
        return {
            "portfolio_id": str(portfolio_id),
            "portfolio_name": portfolio.name,
            **metrics,
        }

    def add_holding(
        self,
        portfolio_id: UUID,
        company_id: UUID,
        quantity: float,
        average_price: Optional[float],
    ) -> dict[str, Any]:
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        existing = (
            self.db.query(Holding)
            .filter(
                Holding.portfolio_id == portfolio_id,
                Holding.company_id == company_id,
            )
            .first()
        )

        if existing:
            existing.quantity += Decimal(str(quantity))
            if average_price:
                existing.average_price = Decimal(str(average_price))
            self.db.commit()
            return {"holding_id": str(existing.id), "action": "updated"}

        holding = Holding(
            portfolio_id=portfolio_id,
            company_id=company_id,
            quantity=Decimal(str(quantity)),
            average_price=Decimal(str(average_price)) if average_price else None,
        )
        self.db.add(holding)
        self.db.commit()
        self.db.refresh(holding)
        return {"holding_id": str(holding.id), "action": "created"}
