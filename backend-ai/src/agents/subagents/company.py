"""Company analysis sub-agent definition."""

from src.agents.prompts.company import COMPANY_ANALYSIS_PROMPT
from src.agents.tools.financial import (
    get_latest_financials,
    calculate_ratios,
    detect_risk_flags,
)
from src.agents.tools.vector_search import search_filings
from src.agents.tools.news import get_recent_news


def get_company_subagent() -> dict:
    """Return the company-analysis sub-agent configuration."""
    return {
        "name": "company-analysis",
        "description": (
            "Perform a deep-dive analysis of a single company: "
            "financials, ratios, risk flags, filing search, and recent news. "
            "Pass the company_id (UUID string) in your task prompt."
        ),
        "system_prompt": COMPANY_ANALYSIS_PROMPT,
        "tools": [
            get_latest_financials,
            calculate_ratios,
            detect_risk_flags,
            search_filings,
            get_recent_news,
        ],
    }
