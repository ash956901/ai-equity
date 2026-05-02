"""Thematic discovery sub-agent."""

from src.agents.prompts.thematic import THEMATIC_DISCOVERY_PROMPT
from src.agents.tools.vector_search import thematic_discovery_search


def get_thematic_subagent() -> dict:
    """Return the thematic discovery sub-agent configuration."""
    return {
        "name": "thematic-discovery",
        "description": "Discovers companies matching macroeconomic, technological, or industry themes (e.g., 'AI companies', 'Renewable Energy') using global vector search.",
        "system_prompt": THEMATIC_DISCOVERY_PROMPT,
        "tools": [thematic_discovery_search],
    }
