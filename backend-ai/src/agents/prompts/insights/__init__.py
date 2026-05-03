"""Per-insight-type prompt templates for the InsightDiscoveryAgent.

Each module exposes ``TEMPLATE`` (a string with placeholders) and
``build_messages(context)`` returning a list of LangChain messages.
"""

from src.agents.prompts.insights.causal_cross_industry import (
    TEMPLATE as CAUSAL_CROSS_INDUSTRY_TEMPLATE,
    build_messages as build_causal_cross_industry_messages,
)
from src.agents.prompts.insights.supply_chain_ripple import (
    TEMPLATE as SUPPLY_CHAIN_RIPPLE_TEMPLATE,
    build_messages as build_supply_chain_ripple_messages,
)
from src.agents.prompts.insights.sentiment_driven import (
    TEMPLATE as SENTIMENT_DRIVEN_TEMPLATE,
    build_messages as build_sentiment_driven_messages,
)
from src.agents.prompts.insights.event_catalyst import (
    TEMPLATE as EVENT_CATALYST_TEMPLATE,
    build_messages as build_event_catalyst_messages,
)


__all__ = [
    "CAUSAL_CROSS_INDUSTRY_TEMPLATE",
    "SUPPLY_CHAIN_RIPPLE_TEMPLATE",
    "SENTIMENT_DRIVEN_TEMPLATE",
    "EVENT_CATALYST_TEMPLATE",
    "build_causal_cross_industry_messages",
    "build_supply_chain_ripple_messages",
    "build_sentiment_driven_messages",
    "build_event_catalyst_messages",
]
