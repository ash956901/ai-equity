"""Sub-agent definitions for the orchestrator."""

from src.agents.subagents.company import get_company_subagent
from src.agents.subagents.comparison import get_comparison_subagent
from src.agents.subagents.discovery import get_discovery_subagent
from src.agents.subagents.doc_insight import get_doc_insight_subagent
from src.agents.subagents.graph_reasoning import get_graph_reasoning_subagent
from src.agents.subagents.macro_commodity import get_macro_commodity_subagent
from src.agents.subagents.news import get_news_subagent
from src.agents.subagents.policy_macro import get_policy_macro_subagent
from src.agents.subagents.portfolio import get_portfolio_subagent
from src.agents.subagents.theme_explorer import get_theme_explorer_subagent
from src.agents.subagents.transcript_analyst import get_transcript_analyst_subagent


def get_all_subagents() -> list[dict]:
    """Return the full list of sub-agent config dicts for create_deep_agent."""
    return [
        get_company_subagent(),
        get_comparison_subagent(),
        get_discovery_subagent(),
        get_portfolio_subagent(),
        get_news_subagent(),
        get_doc_insight_subagent(),
        get_policy_macro_subagent(),
        get_theme_explorer_subagent(),
        get_transcript_analyst_subagent(),
        get_macro_commodity_subagent(),
        get_graph_reasoning_subagent(),
    ]


__all__ = ["get_all_subagents"]
