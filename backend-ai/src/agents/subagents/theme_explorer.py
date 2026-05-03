"""Theme Explorer sub-agent definition."""

from src.agents.prompts.theme_explorer import THEME_EXPLORER_PROMPT
from src.agents.tools.insights import list_daily_insights
from src.agents.tools.relations import reverse_relations
from src.agents.tools.themes import get_company_themes, search_themes
from src.agents.tools.transcripts import search_transcripts
from src.agents.tools.vector_search import search_filings, search_news_semantic


def get_theme_explorer_subagent() -> dict:
    """Return the theme-explorer sub-agent configuration."""
    return {
        "name": "theme-explorer",
        "description": (
            "Explore the most-exposed Indian equities for a theme (AI, ethanol, "
            "EVs, defence, etc.) using company_themes + insight cards."
        ),
        "system_prompt": THEME_EXPLORER_PROMPT,
        "tools": [
            search_themes,
            get_company_themes,
            list_daily_insights,
            reverse_relations,
            search_filings,
            search_transcripts,
            search_news_semantic,
        ],
    }
