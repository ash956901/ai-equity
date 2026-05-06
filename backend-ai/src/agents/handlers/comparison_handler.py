import json
from sqlalchemy.orm import Session
from src.domains.compare.service import CompareService
from src.agents.handlers.synthesis import synthesize_response, extract_companies_from_query

def handle_comparison(query: str, db: Session, user_id: str, expertise_level: str) -> str:
    companies = extract_companies_from_query(query)
    if len(companies) < 2:
        return "I couldn't identify two companies to compare. Please specify them clearly, e.g., 'Compare TCS and Infosys'."
        
    compare_service = CompareService(db)
    try:
        result = compare_service.compare(
            user_id=str(user_id),
            company_names=companies,
            query=query,
            expertise_level=expertise_level
        )
        return synthesize_response(json.dumps(result, default=str), query)
    except Exception as e:
        return f"Sorry, I couldn't compare those companies: {str(e)}"
