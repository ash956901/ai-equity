import json
import uuid
from sqlalchemy.orm import Session
from src.domains.portfolio.service import PortfoliosService

def handle_portfolio(query: str, db: Session, user_id: str, expertise_level: str) -> str:
    service = PortfoliosService(db)
    try:
        # get_ai_suggestions internally uses the research agent
        # and returns a synthesized text response directly.
        uid = uuid.UUID(str(user_id))
        result = service.get_ai_suggestions(uid)
        return result.get("suggestions", "No suggestions available.")
    except Exception as e:
        return f"Sorry, I couldn't fetch your portfolio insights: {str(e)}"
