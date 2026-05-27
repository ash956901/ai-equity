"""Business logic for portfolio endpoints."""

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.agents import build_research_agent
from src.db.models import Company, Holding, Portfolio, User
from src.services.portfolio_service import PortfolioService
from src.utils.data_sources import portfolio_sources


class PortfoliosService:
    """Handles portfolio CRUD and holdings operations."""

    def __init__(self, db: Session):
        self.db = db
        self._portfolio_service = PortfolioService(db)

    def get_ai_suggestions(self, user_id: UUID) -> dict[str, Any]:
        """Generate AI-driven investment suggestions for the user's primary portfolio."""
        portfolio_id = self._portfolio_service.get_primary_portfolio(user_id)
        if not portfolio_id:
            return {"suggestions": "No primary portfolio found. Add one to get AI insights."}

        # Get causal insights first
        causal_context = self._get_causal_context(portfolio_id)

        # Pre-fetch portfolio holdings to avoid tool round-trips
        holdings_context = self._get_holdings_context(portfolio_id)

        agent = build_research_agent()

        task = (
            "You are an expert equity analyst. Below is a complete portfolio with "
            "holdings and market signals. Analyze it directly — do NOT call tools.\n\n"
            f"{holdings_context}\n\n"
            f"{causal_context}\n\n"
            "## Required Output\n\n"
            "### 1. Portfolio Overview\n"
            "A table with columns: Stock (Ticker), Sector, Weight (%), "
            "Recent Signal (1-line catalyst or risk).\n\n"
            "### 2. Hidden Insights (3 specific insights)\n"
            "Connect the commodity changes above to specific holdings. "
            "For each, provide:\n"
            "- **Causal Chain**: commodity move -> sector impact -> company effect\n"
            "- **Confidence**: High/Medium/Low with brief reason\n"
            "- **Action**: Buy more / Hold / Reduce — specific and justified\n\n"
            "### 3. Investment Suggestions\n"
            "Per-stock recommendation with a brief reason. "
            "Then a suggested rebalancing move (e.g., trim X by 2%, add to Y by 2%).\n\n"
            "### 4. Explained Simply\n"
            "2-3 sentence plain-language bottom line for a retail investor.\n\n"
            "Be specific. Name actual stocks from the portfolio. "
            "Use INR and Cr (crore). Never fabricate data."
        )


        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": task}]},
                config={"configurable": {"thread_id": f"suggestions-{user_id}"}},
            )
            response_text = result["messages"][-1].content
            return {"suggestions": response_text}
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to generate AI suggestions: {e}")
            return {"suggestions": "AI insights are temporarily unavailable. Please try again later."}

    def _get_holdings_context(self, portfolio_id: UUID) -> str:
        """Get portfolio holdings as structured context for the agent."""
        try:
            holdings = (
                self.db.query(Holding)
                .filter(Holding.portfolio_id == portfolio_id)
                .all()
            )
            total_qty = sum(float(h.quantity) for h in holdings)
            if not total_qty:
                return "Portfolio has no holdings."

            lines = ["## Portfolio Holdings\n"]
            for h in holdings:
                company = self.db.query(Company).filter(Company.id == h.company_id).first()
                name = company.name if company else "Unknown"
                ticker = (company.ticker_nse or company.ticker_bse or "N/A") if company else "N/A"
                sector = company.sector if company else "N/A"
                qty = float(h.quantity)
                weight = (qty / total_qty * 100) if total_qty > 0 else 0
                lines.append(
                    f"- {name} ({ticker}) | {sector} | "
                    f"{qty:.0f} shares | {weight:.1f}% weight"
                )
            return "\n".join(lines)
        except Exception:
            return "Portfolio holdings unavailable."

    def _get_causal_context(self, portfolio_id: UUID) -> str:
        """Get causal context for portfolio analysis."""
        try:
            from src.services.causal_service import CausalService
            
            causal_service = CausalService(self.db)
            insights = causal_service.analyze_portfolio(portfolio_id)
            
            if not insights:
                # Get commodity changes as fallback using CausalService method
                changes = causal_service.get_commodity_changes(days=7)
                volatile = [
                    f"- {k}: {v.get('change_pct', 0):+.1f}%" 
                    for k, v in changes.items() 
                    if abs(v.get('change_pct', 0)) >= 3
                ]
                if volatile:
                    return "## Commodity Price Changes (7-day)\n" + "\n".join(volatile[:5])
                return "No significant commodity price changes detected in the past week."
            
            # Format insights as context for agent
            context_lines = ["## Current Market Signals Affecting Your Portfolio\n"]
            
            for i, insight in enumerate(insights[:5], 1):
                direction = "↑" if insight.get("price_change_pct", 0) > 0 else "↓"
                context_lines.append(
                    f"{i}. **{insight.get('ticker', 'Company')}** ({insight.get('sector', 'N/A')}): "
                    f"{insight.get('commodity_name', insight.get('commodity'))} {direction} "
                    f"{abs(insight.get('price_change_pct', 0)):.1f}% - "
                    f"{insight.get('impact_direction', 'neutral').title()} impact"
                )
            
            return "\n".join(context_lines)
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not get causal context: {e}")
            return "No causal data available at this time."


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
