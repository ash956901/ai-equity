import json
from sqlalchemy.orm import Session
from src.agents.handlers.synthesis import synthesize_response
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.financial import get_latest_financials, calculate_ratios
from src.agents.tools.news import get_recent_news
from src.agents.tools.web_search import internet_search
from src.db.database import get_db

def _extract_entity(query: str) -> str:
    """Extract a likely entity name or search term from the query."""
    words = query.split()
    skip = {"analyze", "tell", "me", "about", "what", "is", "the", "news", "recent", "on", "for", "company", "event:", "this", "timeline"}
    candidates = []
    for word in words:
        clean_word = word.strip(":.,!?()\"'")
        if clean_word.lower() not in skip and len(clean_word) > 2:
            candidates.append(clean_word)
    return " ".join(candidates[:3]) if candidates else query

def handle_analysis(query: str, db: Session, user_id: str, expertise_level: str) -> str:
    """Directly fetch company data and synthesize."""
    entity = _extract_entity(query)
    
    # Try to resolve company
    try:
        company_info = resolve_company.invoke({"name_or_ticker": entity})
        if isinstance(company_info, dict) and "error" not in company_info and "company_id" in company_info:
            c_id = company_info["company_id"]
            financials = get_latest_financials.invoke({"company_id": c_id, "periods": 2})
            ratios = calculate_ratios.invoke({"company_id": c_id})
            
            raw_data = {
                "company": company_info,
                "financials": financials,
                "ratios": ratios
            }
            return synthesize_response(json.dumps(raw_data, default=str), query, f"Expertise: {expertise_level}")
    except Exception:
        pass
        
    # Fallback to search if company resolution fails
    return handle_general(query, db, user_id, expertise_level)

def handle_news(query: str, db: Session, user_id: str, expertise_level: str) -> str:
    """Directly fetch news and synthesize."""
    entity = _extract_entity(query)
    
    try:
        company_info = resolve_company.invoke({"name_or_ticker": entity})
        if isinstance(company_info, dict) and "error" not in company_info and "company_id" in company_info:
            c_id = company_info["company_id"]
            news = get_recent_news.invoke({"company_id": c_id, "days": 30, "limit": 10})
            
            raw_data = {
                "company": company_info,
                "news": news
            }
            return synthesize_response(json.dumps(raw_data, default=str), query, f"Expertise: {expertise_level}")
    except Exception:
        pass
        
    # Fallback to search
    return handle_general(query, db, user_id, expertise_level)

def handle_general(query: str, db: Session, user_id: str, expertise_level: str) -> str:
    """Use the full reactive agent for complex, non-deterministic queries to restore maximum intelligence."""
    from src.agents.orchestrator import build_research_agent
    
    agent = build_research_agent()
    
    # We must formulate a clear message for the agent
    prompt = f"User Query: {query}\n\nExpertise Level: {expertise_level}\n\nPlease analyze this using your available tools. Be comprehensive but concise."
    
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": f"general-{user_id}"}},
        )
        return getattr(result["messages"][-1], "content", str(result["messages"][-1]))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed in handle_general: {e}")
        # Final fallback
        return f"Sorry, I encountered an issue analyzing that request: {str(e)}"
