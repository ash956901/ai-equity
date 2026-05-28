"""Performance & Learnings sub-agent definition."""

from src.agents.prompts.performance import PERFORMANCE_PROMPT
from src.agents.tools.portfolio import (
    get_portfolio_holdings,
    calculate_portfolio_metrics,
    get_user_primary_portfolio,
)
from src.agents.tools.performance_tools import (
    get_portfolio_performance,
    compare_to_benchmark,
    extract_learnings,
    get_today_trades,
)


def get_performance_subagent() -> dict:
    """Return the performance & learnings sub-agent configuration."""
    return {
        "name": "performance-learnings",
        "description": (
            "Analyse portfolio performance over a time period: returns, winners, losers, "
            "benchmark comparison against Nifty 50, and 3-5 concrete investment learnings. "
            "Use when the user asks about their returns, P&L, performance, "
            "best/worst trades, or what they've learned from their portfolio."
        ),
        "system_prompt": PERFORMANCE_PROMPT,
        "tools": [
            get_user_primary_portfolio,
            get_portfolio_holdings,
            calculate_portfolio_metrics,
            get_portfolio_performance,
            compare_to_benchmark,
            extract_learnings,
            get_today_trades,
        ],
    }
