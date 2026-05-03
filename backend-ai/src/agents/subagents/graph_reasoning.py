"""Graph Reasoning sub-agent definition (Phase 2)."""

from src.agents.prompts.graph_reasoning import GRAPH_REASONING_PROMPT
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.graph import traverse_graph
from src.agents.tools.insights import list_daily_insights
from src.agents.tools.relations import get_relations, reverse_relations


def get_graph_reasoning_subagent() -> dict:
    """Return the graph-reasoning sub-agent configuration."""
    return {
        "name": "graph-reasoning",
        "description": (
            "Multi-hop reasoning over the relation graph (Phase 2). Use for "
            "supplier-of-supplier questions, second-order policy effects, or "
            "any 'what depends on X' query."
        ),
        "system_prompt": GRAPH_REASONING_PROMPT,
        "tools": [
            traverse_graph,
            get_relations,
            reverse_relations,
            list_daily_insights,
            resolve_company,
        ],
    }
