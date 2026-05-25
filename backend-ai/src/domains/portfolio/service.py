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

        # We use the research agent to generate a summary/suggestion
        agent = build_research_agent()
        
        # Enhanced task with causal context
        task = (
            f"Analyse the portfolio {portfolio_id} and recent market news. "
            "Also consider the following commodity price trends and market signals:\n\n"
            f"{causal_context}\n\n"
            "Provide 3-4 specific 'Hidden Insights' that connect world events and commodity prices "
            "to specific companies in this portfolio. Format each insight as:\n"
            "- **Trigger**: What happened (e.g., 'Oil up 5%')\n"
            "- **Chain**: How it propagates (e.g., 'Oil → Transport costs → Margins')\n"
            "- **Impact**: Which holdings are affected and how\n"
            "- **Confidence**: How certain (High/Medium/Low)\n"
            "- **Recommendation**: What to consider (Buy more/Hold/Reduce)\n\n"
            "Also provide Investment Suggestions (Buy/Sell/Hold) for this user. "
            "Return the response as a clean, professional markdown block with headers and bullet points. "
            "Do NOT return JSON or structured lists, just formatted text."
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

    def delete_portfolio(self, portfolio_id: UUID, user_id: UUID) -> dict[str, Any]:
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        if portfolio.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorised to delete this portfolio")
        self.db.delete(portfolio)
        self.db.commit()
        from src.utils.cache import get_analysis_cache
        get_analysis_cache().invalidate(f"portfolio_causal:{portfolio_id}")
        return {"portfolio_id": str(portfolio_id), "deleted": True}

    def delete_holding(self, portfolio_id: UUID, holding_id: UUID) -> dict[str, Any]:
        holding = self.db.query(Holding).filter(
            Holding.id == holding_id,
            Holding.portfolio_id == portfolio_id,
        ).first()
        if not holding:
            raise HTTPException(status_code=404, detail="Holding not found")
        self.db.delete(holding)
        self.db.commit()
        from src.utils.cache import get_analysis_cache
        get_analysis_cache().invalidate(f"portfolio_causal:{portfolio_id}")
        return {"holding_id": str(holding_id), "deleted": True}
