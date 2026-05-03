"""Company analysis sub-agent definition."""

from src.agents.prompts.company import COMPANY_ANALYSIS_PROMPT
from src.agents.tools.financial import (
    calculate_ratios,
    detect_governance_flags,
    detect_risk_flags,
    get_latest_financials,
)
from src.agents.tools.news import get_recent_news
from src.agents.tools.vector_search import search_filings


def get_company_subagent() -> dict:
    """Return the company-analysis sub-agent configuration."""
    return {
        "name": "company-analysis",
        "description": (
            "Perform a deep-dive analysis of a single company: financials, "
            "ratios, financial AND governance risk flags, filing search, and "
            "recent news. Pass the company_id (UUID string) in your task prompt."
        ),
        "system_prompt": COMPANY_ANALYSIS_PROMPT,
        "tools": [
            get_latest_financials,
            calculate_ratios,
            detect_risk_flags,
            detect_governance_flags,
            search_filings,
            get_recent_news,
        ],
    }
