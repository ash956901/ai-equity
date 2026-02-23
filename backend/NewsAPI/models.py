"""
Pydantic models for NewsAPI responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


# ─────────────────────────────────────────────
# Core building blocks
# ─────────────────────────────────────────────

class NewsSource(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class NewsArticle(BaseModel):
    source: Optional[NewsSource] = None
    author: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    urlToImage: Optional[str] = None
    publishedAt: Optional[str] = None
    content: Optional[str] = None


# ─────────────────────────────────────────────
# Endpoint response wrappers
# ─────────────────────────────────────────────

class NewsResponse(BaseModel):
    """Response model for /everything and /top-headlines endpoints."""
    status: str
    totalResults: Optional[int] = None
    articles: Optional[List[NewsArticle]] = None
    message: Optional[str] = None   # present when status == "error"
    code: Optional[str] = None      # NewsAPI error code


class NewsSourceDetail(BaseModel):
    """A single source entry returned by /sources."""
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None


class SourcesResponse(BaseModel):
    """Response model for /sources endpoint."""
    status: str
    sources: Optional[List[NewsSourceDetail]] = None
    message: Optional[str] = None
    code: Optional[str] = None


# ─────────────────────────────────────────────
# Convenience / aggregated models used by routes
# ─────────────────────────────────────────────

class StockNewsResponse(BaseModel):
    """Aggregated news response for a specific stock ticker / company."""
    symbol: str
    company_name: Optional[str] = None
    total_results: int = 0
    articles: List[NewsArticle] = []


class SentimentArticle(BaseModel):
    """Minimal news article enriched with metadata useful for sentiment scoring."""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    publishedAt: Optional[str] = None


class SentimentNewsResponse(BaseModel):
    """Response used by the /news/sentiment/{symbol} route."""
    symbol: str
    total_results: int = 0
    articles: List[SentimentArticle] = []
    note: str = (
        "Articles returned as-is. Pass titles/descriptions to your LLM "
        "for sentiment scoring."
    )
