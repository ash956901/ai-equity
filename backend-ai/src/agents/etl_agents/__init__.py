"""ETL-side agents.

These run inside Celery workers (not the live orchestrator) and produce the
structured + vector-indexed substrate the query-time sub-agents reason over:

- ``filing_agent``: not a separate module yet; the filing crawlers do the
  ingestion themselves and queue parsing.
- ``theme_agent.ThemeTaggingAgent``
- ``event_agent.EventExtractionAgent``
- ``insight_agent.InsightDiscoveryAgent``
- ``revalidation_agent.InsightRevalidationAgent``
"""

from src.agents.etl_agents.event_agent import EventExtractionAgent
from src.agents.etl_agents.graph_backfill import backfill_graph_edges
from src.agents.etl_agents.insight_agent import InsightDiscoveryAgent
from src.agents.etl_agents.pattern_mining_agent import PatternMiningAgent
from src.agents.etl_agents.revalidation_agent import InsightRevalidationAgent
from src.agents.etl_agents.supply_chain_agent import SupplyChainAgent
from src.agents.etl_agents.theme_agent import ThemeTaggingAgent

__all__ = [
    "ThemeTaggingAgent",
    "EventExtractionAgent",
    "InsightDiscoveryAgent",
    "InsightRevalidationAgent",
    "SupplyChainAgent",
    "PatternMiningAgent",
    "backfill_graph_edges",
]
