"""Comparison sub-agent definition."""

from src.agents.prompts.comparison import COMPARISON_PROMPT
from src.agents.tools.financial import get_latest_financials, calculate_ratios
from src.agents.tools.vector_search import search_filings


def get_comparison_subagent() -> dict:
    """Return the comparison sub-agent configuration."""
    return {
        "name": "comparison",
        "description": (
            "Compare 2-5 companies side by side on financials, ratios, and filings. "
            "Pass all company_id UUIDs in your task prompt."
        ),
        "system_prompt": COMPARISON_PROMPT,
        "tools": [
            get_latest_financials,
            calculate_ratios,
            search_filings,
        ],
    }
