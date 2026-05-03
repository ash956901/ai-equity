"""Discovery / Hidden-Insight sub-agent definition.

Surfaces non-obvious thematic exposure (Castrol → Data Centres) and
walks the relation graph for second-order effects. Backed by data the
``ThemeTaggingAgent`` populates offline.
"""

from src.agents.prompts.discovery import DISCOVERY_PROMPT
from src.agents.tools.discovery import (
    find_second_order_effects,
    find_supply_chain_links,
    get_companies_in_theme,
    get_macro_sensitivity,
)
from src.agents.tools.themes import (
    get_asymmetric_company_themes,
    get_company_themes,
    search_themes,
)
from src.agents.tools.relations import get_relations, reverse_relations


def get_discovery_subagent() -> dict:
    """Return the discovery sub-agent configuration for create_deep_agent."""
    return {
        "name": "discovery",
        "description": (
            "Surface HIDDEN / ASYMMETRIC thematic exposure (e.g. Castrol India "
            "→ Data Centres via specialty coolants) and SECOND-ORDER effects of "
            "themes, events, or macro shifts. Pass either a company UUID/name or "
            "a theme/event description in the task prompt. Use this whenever the "
            "user asks about hidden exposure, ripple effects, supply-chain links, "
            "indirect beneficiaries, or 'who else benefits / suffers from X'."
        ),
        "system_prompt": DISCOVERY_PROMPT,
        "tools": [
            get_company_themes,
            get_asymmetric_company_themes,
            search_themes,
            get_companies_in_theme,
            find_second_order_effects,
            find_supply_chain_links,
            get_macro_sensitivity,
            get_relations,
            reverse_relations,
        ],
    }
