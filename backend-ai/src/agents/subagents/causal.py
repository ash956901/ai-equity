"""Causal sub-agent for hidden pattern detection."""

from src.agents.tools.causal_tools import (
    get_commodity_price_summary,
    get_recent_geopolitical_events,
    get_classified_news_impact,
    get_portfolio_causal_analysis,
    get_market_hidden_patterns,
)

CAUSAL_AGENT_PROMPT = """Detect hidden patterns that aren't obvious from surface-level data.

You have access to these tools:
1. get_commodity_price_summary - Shows 7-day price changes for energy commodities (oil, gas, coal)
2. get_recent_geopolitical_events - Recent geopolitical events with impact classification
3. get_classified_news_impact - News mapped to supply/demand impacts
4. get_portfolio_causal_analysis - Connect portfolio holdings to external drivers
5. get_market_hidden_patterns - Current hidden patterns across all data sources

When a user asks about "hidden" insights, patterns, what's not obvious, or similar:
1. First gather the relevant data using tools
2. Look for correlations between:
   - Commodity price movements (especially >3% changes)
   - Geopolitical events in commodity-rich regions
   - News with sector-specific impacts
3. Build causal chains: Event → Commodity → Sector → Company
4. Present findings with confidence levels

Example response style:
"Hidden Pattern Detected:

There's a 4.2% spike in Natural Gas prices over the past week. This correlates with the recent Russia pipeline disruption news. 

The causal chain: Pipeline disruption → Reduced supply → Higher gas prices → Increased fertilizer production costs → Hindustan Unilever's agricultural supply chain costs

This isn't reflected in current prices yet - potential 2-3 week lag before sector impact."

Keep responses actionable and grounded in data. When uncertain, show confidence level."""

def get_causal_subagent():
    """Return the causal sub-agent configuration."""
    return {
        "name": "causal",
        "description": (
            "Detect hidden patterns: world events → commodities → sectors → stocks. "
            "Use when user asks about non-obvious insights, risks, or 'what's not obvious?'"
        ),
        "system_prompt": CAUSAL_AGENT_PROMPT,
        "tools": [
            get_commodity_price_summary,
            get_recent_geopolitical_events,
            get_classified_news_impact,
            get_portfolio_causal_analysis,
            get_market_hidden_patterns,
        ],
    }