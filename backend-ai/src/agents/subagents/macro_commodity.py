"""Macro + Commodity sub-agent definition."""

from src.agents.prompts.macro_commodity import MACRO_COMMODITY_PROMPT
from src.agents.tools.insights import list_daily_insights
from src.agents.tools.macro import (
    commodity_exposure,
    get_commodity_series,
    get_macro_series,
)
from src.agents.tools.relations import reverse_relations
from src.agents.tools.themes import get_company_themes


def get_macro_commodity_subagent() -> dict:
    """Return the macro-commodity sub-agent configuration."""
    return {
        "name": "macro-commodity",
        "description": (
            "Connect macro / commodity / FX moves to Indian equity exposure "
            "via sector_commodity_links and relation edges."
        ),
        "system_prompt": MACRO_COMMODITY_PROMPT,
        "tools": [
            get_macro_series,
            get_commodity_series,
            commodity_exposure,
            reverse_relations,
            get_company_themes,
            list_daily_insights,
        ],
    }
