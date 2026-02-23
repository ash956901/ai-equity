"""
Pydantic models for NewsData.io API responses.

Response schema source: https://newsdata.io/documentation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


# ─────────────────────────────────────────────
# Core article model (shared across all endpoints)
# ─────────────────────────────────────────────

class NewsDataArticle(BaseModel):
    """Full article object returned by NewsData.io."""
    article_id: Optional[str] = None
    title: Optional[str] = None
    link: Optional[str] = None
    keywords: Optional[List[str]] = None
    creator: Optional[List[str]] = None
    video_url: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    pubDate: Optional[str] = None
    pubDateTZ: Optional[str] = None
    fetched_at: Optional[str] = None
    image_url: Optional[str] = None
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_icon: Optional[str] = None
    source_priority: Optional[int] = None
    country: Optional[List[str]] = None
    category: Optional[List[str]] = None
    language: Optional[str] = None
    datatype: Optional[str] = None
    duplicate: Optional[bool] = None
    # Market-specific
    symbol: Optional[List[str]] = None
    # Crypto-specific (coin is included in keywords for crypto endpoint)
    # Pro/Corporate plan fields
    ai_tag: Optional[List[str]] = None
    ai_region: Optional[List[str]] = None
    ai_org: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_stats: Optional[Dict[str, float]] = None


# ─────────────────────────────────────────────
# Generic list-response wrapper
# ─────────────────────────────────────────────

class NewsDataResponse(BaseModel):
    """
    Wraps any NewsData.io list endpoint response
    (latest, market, crypto, archive).
    """
    status: str
    totalResults: Optional[int] = None
    results: Optional[List[NewsDataArticle]] = None
    nextPage: Optional[str] = None
    # Error fields
    message: Optional[str] = None
    code: Optional[str] = None


# ─────────────────────────────────────────────
# Sources endpoint models
# ─────────────────────────────────────────────

class NewsDataSource(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[List[str]] = None
    language: Optional[List[str]] = None
    country: Optional[List[str]] = None
    last_fetch: Optional[str] = None


class NewsDataSourcesResponse(BaseModel):
    status: str
    results: Optional[List[NewsDataSource]] = None
    message: Optional[str] = None
    code: Optional[str] = None


# ─────────────────────────────────────────────
# Count endpoint models
# ─────────────────────────────────────────────

class CountEntry(BaseModel):
    """One row of the count breakdown (by day or hour)."""
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    count: Optional[int] = None


class NewsDataCountResponse(BaseModel):
    status: str
    totalResults: Optional[int] = None
    results: Optional[List[CountEntry]] = None
    message: Optional[str] = None
    code: Optional[str] = None


# ─────────────────────────────────────────────
# Equity-agent convenience models
# ─────────────────────────────────────────────

class MarketNewsResponse(BaseModel):
    """Typed wrapper for market-endpoint results with equity metadata."""
    status: str
    totalResults: Optional[int] = None
    results: Optional[List[NewsDataArticle]] = None
    nextPage: Optional[str] = None
    message: Optional[str] = None
    code: Optional[str] = None


class TickerNewsResponse(BaseModel):
    """News articles for a specific stock ticker (from /market?symbol=...)."""
    symbol: str
    total_results: int = 0
    articles: List[NewsDataArticle] = []
    next_page: Optional[str] = None


class SentimentFeedArticle(BaseModel):
    """Stripped-down article for LLM sentiment scoring."""
    article_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    source_name: Optional[str] = None
    link: Optional[str] = None
    pubDate: Optional[str] = None
    sentiment: Optional[str] = None          # if Pro/Corporate plan
    sentiment_stats: Optional[Dict[str, float]] = None
    ai_summary: Optional[str] = None         # if Pro/Corporate plan


class SentimentFeedResponse(BaseModel):
    """Sentiment-optimised feed for a ticker, ready for LLM ingestion."""
    symbol: str
    total_results: int = 0
    articles: List[SentimentFeedArticle] = []
    next_page: Optional[str] = None
    note: str = (
        "Articles enriched with sentiment/ai_summary when available "
        "(Pro/Corporate plans). Pass title + description + content to "
        "your LLM for custom scoring on free-tier keys."
    )
