import re
from enum import Enum

class QueryRoute(str, Enum):
    COMPARE = "compare"
    PORTFOLIO = "portfolio"
    CAUSAL = "causal"
    ANALYZE = "analyze"
    NEWS = "news"
    GENERAL = "general"

def route_query(query: str) -> QueryRoute:
    """Classify query type and return handler."""
    query_lower = query.lower()
    
    # Causal detection: "not obvious", "hidden", "pattern", "risk", "causal"
    if re.search(r'\b(not obvious|hidden|pattern|risk|causal)\b', query_lower):
        return QueryRoute.CAUSAL
        
    # Compare detection: "compare", "vs", "versus"
    if re.search(r'\b(compare|vs|versus)\b', query_lower):
        return QueryRoute.COMPARE
        
    # Portfolio detection: "portfolio", "holdings", "my stocks", "suggestions"
    if re.search(r'\b(portfolio|holdings|my stocks|suggestions)\b', query_lower):
        return QueryRoute.PORTFOLIO

    # Analysis detection: "analyze", "deep dive", "financials"
    if re.search(r'\b(analyze|deep dive|financials)\b', query_lower):
        return QueryRoute.ANALYZE
        
    # News detection: "news", "recent", "headlines"
    if re.search(r'\b(news|recent|headlines)\b', query_lower):
        return QueryRoute.NEWS
        
    return QueryRoute.GENERAL
