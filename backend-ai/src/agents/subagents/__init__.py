"""Sub-agent definitions for the orchestrator."""

from src.agents.subagents.company import get_company_subagent
from src.agents.subagents.comparison import get_comparison_subagent
from src.agents.subagents.portfolio import get_portfolio_subagent
from src.agents.subagents.news import get_news_subagent
from src.agents.subagents.doc_insight import get_doc_insight_subagent


def get_all_subagents() -> list[dict]:
    """Return the full list of sub-agent config dicts for create_deep_agent."""
    return [
        get_company_subagent(),
        get_comparison_subagent(),
        get_portfolio_subagent(),
        get_news_subagent(),
        get_doc_insight_subagent(),
    ]


__all__ = ["get_all_subagents"]
