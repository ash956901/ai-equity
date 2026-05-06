import json
import uuid
from sqlalchemy.orm import Session
from src.services.causal_service import CausalService
from src.services.portfolio_service import PortfolioService
from src.agents.handlers.synthesis import synthesize_response

def handle_causal(query: str, db: Session, user_id: str, expertise_level: str) -> str:
    causal_service = CausalService(db)
    portfolio_service = PortfolioService(db)
    
    uid = uuid.UUID(str(user_id))
    primary_portfolio_id = portfolio_service.get_primary_portfolio(uid)
    
    try:
        if primary_portfolio_id:
            insights = causal_service.analyze_portfolio(primary_portfolio_id)
            if insights:
                raw_data = {"portfolio_causal_insights": insights}
            else:
                raw_data = {"commodity_changes": causal_service.get_commodity_changes(days=7)}
        else:
            raw_data = {"commodity_changes": causal_service.get_commodity_changes(days=7)}
            
        return synthesize_response(json.dumps(raw_data, default=str), query)
    except Exception as e:
        return f"Sorry, I couldn't fetch causal insights: {str(e)}"
