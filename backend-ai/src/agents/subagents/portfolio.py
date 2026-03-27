"""Portfolio sub-agent definition."""

from src.agents.prompts.portfolio import PORTFOLIO_PROMPT
from src.agents.tools.portfolio import (
    get_portfolio_holdings,
    calculate_portfolio_metrics,
    get_user_primary_portfolio,
)
from src.agents.tools.news import get_recent_news


def get_portfolio_subagent() -> dict:
    """Return the portfolio sub-agent configuration."""
    return {
        "name": "portfolio",
        "description": (
            "Analyse a user's portfolio: holdings, allocation, concentration, "
            "risk metrics, and news for top holdings. "
            "Pass the user_id or portfolio_id in your task prompt."
        ),
        "system_prompt": PORTFOLIO_PROMPT,
        "tools": [
            get_portfolio_holdings,
            calculate_portfolio_metrics,
            get_user_primary_portfolio,
            get_recent_news,
        ],
    }
