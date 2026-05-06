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

        # Get holdings
        holdings = self._portfolio_service.get_holdings(portfolio_id)
        if not holdings:
            return {"suggestions": "Your primary portfolio is empty. Add holdings to get AI insights."}
            
        enriched_holdings = []
        for h in holdings:
            c = self.db.query(Company).filter(Company.id == h['company_id']).first()
            name = c.name if c else "Unknown Company"
            ticker = c.ticker_nse or c.ticker_bse if c else "Unknown"
            enriched_holdings.append(f"- {name} ({ticker}) - Quantity: {h.get('quantity')}")
            h['company_name'] = name
            
        holdings_text = "\\n".join(enriched_holdings)

        # Get recent news for top 3 holdings
        from src.services.news_service import NewsService
        news_svc = NewsService(self.db)
        news_context = []
        for h in holdings[:3]:
            cid = h.get('company_id')
            if cid:
                import uuid
                try:
                    news_items = news_svc.get_recent_news(uuid.UUID(str(cid)), days=30, limit=2)
                    if news_items:
                        news_context.append(f"**{h.get('company_name')} News:**")
                        for n in news_items:
                            news_context.append(f"- {n.get('title')} ({n.get('sentiment', 'neutral')})")
                except Exception:
                    pass
        news_text = "\\n".join(news_context) if news_context else "No recent news for top holdings."

        # Get causal insights
        causal_context = self._get_causal_context(portfolio_id)

        # Use a direct, fast LLM call without tools to avoid binding crashes
        from src.agents.handlers.synthesis import get_synthesis_llm
        from langchain_core.messages import HumanMessage
        llm = get_synthesis_llm()
        
        task = (
            "You are Iris, a highly intelligent senior equity research analyst specializing in Indian markets.\n"
            "You are reviewing a user's portfolio to provide top-tier, actionable investment suggestions.\n\n"
            f"**Portfolio Holdings:**\n{holdings_text}\n\n"
            f"**Recent News for Top Holdings:**\n{news_text}\n\n"
            f"**Market & Commodity Signals:**\n{causal_context}\n\n"
            "Synthesize this data into a brilliant, highly readable report. Do not be generic; provide specific, thesis-driven analysis.\n"
            "You MUST output EXACTLY this markdown structure:\n\n"
            "## AI Investment Suggestions\n\n"
            "## Recent News for Top Holdings\n"
            "(Provide a brief, insightful summary of the recent news affecting the top holdings. Do not just list headlines; explain the sentiment and meaning.)\n\n"
            "## Hidden Insights (Alpha Signals)\n"
            "(Identify 3-4 deep, non-obvious causal links connecting the macro/commodity signals to specific portfolio holdings.)\n"
            "### 1\n"
            "* **Trigger:** [What macroeconomic event or commodity shift occurred?]\n"
            "* **Chain:** [How does it flow through the economy? e.g. Event → Input Cost → Margin → Company]\n"
            "* **Impact:** [Which specific holding is affected and how?]\n"
            "* **Confidence:** [High / Medium / Low]\n"
            "* **Recommendation:** [Specific actionable advice]\n"
            "(Repeat for insights 2, 3, etc.)\n\n"
            "---\n\n"
            "# Investment Suggestions (Buy / Sell / Hold)\n"
            "(List every major holding. Be decisive. Provide a 1-sentence analytical reason for the rating based on the data.)\n"
            "* **[Company Name]:** [Buy / Sell / Hold] — [Reasoning]\n\n"
            "---\n\n"
            "# Explained Simply\n"
            "(Provide a plain-English summary for a retail investor.)\n"
            "* **Why you own it:** [Summary of portfolio composition]\n"
            "* **How it's doing:** [Overall health/performance based on news & signals]\n"
            "* **Risk:** [Key risks identified in causal analysis]\n"
            "* **Good news:** [Key tailwinds]\n"
            "* **Caution:** [What to watch out for]\n\n"
            "Ensure the response is extremely high quality, readable, and directly ties the causal data to the holdings."
        )

        try:
            result = llm.invoke([HumanMessage(content=task)])
            response_text = getattr(result, "content", str(result))
            return {"suggestions": response_text}
        except Exception as e:
            import logging
            print(f"DEBUG: Exception in get_ai_suggestions: {e}")
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
