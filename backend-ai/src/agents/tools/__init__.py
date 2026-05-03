"""Consolidated tool registry for all agents and sub-agents."""

from src.agents.tools.financial import (
    calculate_ratios,
    detect_governance_flags,
    detect_risk_flags,
    get_latest_financials,
)
from src.agents.tools.vector_search import (
    search_filings,
    search_news_semantic,
    search_user_upload,
)
from src.agents.tools.portfolio import (
    get_portfolio_holdings,
    calculate_portfolio_metrics,
    get_user_primary_portfolio,
)
from src.agents.tools.news import get_recent_news
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.document import parse_pdf, parse_ppt, fetch_url
from src.agents.tools.web_search import internet_search

# Phase-1 insight engine tools
from src.agents.tools.themes import get_company_themes, search_themes
from src.agents.tools.events import search_events
from src.agents.tools.insights import get_insight, list_daily_insights
from src.agents.tools.transcripts import (
    get_transcript_segments,
    list_recent_transcripts,
    search_transcripts,
)
from src.agents.tools.macro import (
    commodity_exposure,
    get_commodity_series,
    get_macro_series,
)
from src.agents.tools.social import search_social
from src.agents.tools.relations import get_relations, reverse_relations

# Round 1 Discovery vertical tools (asymmetric / second-order / macro)
from src.agents.tools.themes import get_asymmetric_company_themes
from src.agents.tools.discovery import (
    find_second_order_effects,
    find_supply_chain_links,
    get_companies_in_theme,
    get_macro_sensitivity,
)
from src.agents.tools.graph import traverse_graph

__all__ = [
    "get_latest_financials",
    "calculate_ratios",
    "detect_risk_flags",
    "detect_governance_flags",
    "search_filings",
    "search_news_semantic",
    "search_user_upload",
    "get_portfolio_holdings",
    "calculate_portfolio_metrics",
    "get_user_primary_portfolio",
    "get_recent_news",
    "resolve_company",
    "parse_pdf",
    "parse_ppt",
    "fetch_url",
    "internet_search",
    # insight engine tools
    "search_themes",
    "get_company_themes",
    "search_events",
    "list_daily_insights",
    "get_insight",
    "search_transcripts",
    "list_recent_transcripts",
    "get_transcript_segments",
    "get_macro_series",
    "get_commodity_series",
    "commodity_exposure",
    "search_social",
    "get_relations",
    "reverse_relations",
    # Discovery vertical (Round 1)
    "get_asymmetric_company_themes",
    "get_companies_in_theme",
    "find_second_order_effects",
    "find_supply_chain_links",
    "get_macro_sensitivity",
    "traverse_graph",
]
