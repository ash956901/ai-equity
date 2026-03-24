"""Consolidated tool registry for all agents and sub-agents."""

from src.agents.tools.financial import (
    get_latest_financials,
    calculate_ratios,
    detect_risk_flags,
)
from src.agents.tools.vector_search import search_filings, search_user_upload
from src.agents.tools.portfolio import (
    get_portfolio_holdings,
    calculate_portfolio_metrics,
    get_user_primary_portfolio,
)
from src.agents.tools.news import get_recent_news
from src.agents.tools.company_resolver import resolve_company
from src.agents.tools.document import parse_pdf, parse_ppt, fetch_url
from src.agents.tools.web_search import internet_search

__all__ = [
    "get_latest_financials",
    "calculate_ratios",
    "detect_risk_flags",
    "search_filings",
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
]
