"""Policy + Macro sub-agent definition."""

from src.agents.prompts.policy_macro import POLICY_MACRO_PROMPT
from src.agents.tools.events import search_events
from src.agents.tools.insights import list_daily_insights
from src.agents.tools.macro import (
    commodity_exposure,
    get_commodity_series,
    get_macro_series,
)
from src.agents.tools.relations import get_relations, reverse_relations
from src.agents.tools.themes import get_company_themes, search_themes
from src.agents.tools.vector_search import search_news_semantic


def get_policy_macro_subagent() -> dict:
    """Return the policy_macro sub-agent configuration."""
    return {
        "name": "policy-macro",
        "description": (
            "Map a government policy or macro driver to its likely Indian-equity "
            "winners and losers. Cite events, themes, and relation edges."
        ),
        "system_prompt": POLICY_MACRO_PROMPT,
        "tools": [
            search_events,
            search_themes,
            get_company_themes,
            get_macro_series,
            get_commodity_series,
            commodity_exposure,
            get_relations,
            reverse_relations,
            list_daily_insights,
            search_news_semantic,
        ],
    }
