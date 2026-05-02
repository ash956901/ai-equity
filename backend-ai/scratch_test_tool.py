import logging
from src.db.database import SessionLocal
from src.agents.tools._utils import resolve_company_id
from src.agents.tools.vector_search import search_filings, thematic_discovery_search

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
try:
    uid = resolve_company_id("Reliance Industries", db)
    print(f"Resolved UID: {uid}")
    
    # Test vector search directly
    print("\nTesting search_filings tool...")
    results = search_filings.invoke({
        "company_id": "Reliance Industries",
        "query": "risk factors revenue growth"
    })
    print(results)
    
    # Test thematic search directly
    print("\nTesting thematic_discovery_search tool...")
    thematic_results = thematic_discovery_search.invoke({
        "query": "revenue growth and debt reduction"
    })
    print(thematic_results)
finally:
    db.close()
