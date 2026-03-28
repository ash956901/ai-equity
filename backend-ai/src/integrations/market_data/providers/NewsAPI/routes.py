"""
FastAPI routes for NewsAPI endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List

from .client import NewsAPIClient
from .models import (
    NewsResponse,
    SourcesResponse,
    StockNewsResponse,
    SentimentNewsResponse,
    NewsArticle,
    SentimentArticle,
    NewsSource,
)

router = APIRouter(prefix="/news", tags=["News API"])
news_client = NewsAPIClient()


# ─────────────────────────────────────────────
# /news/headlines
# ─────────────────────────────────────────────

@router.get("/headlines", response_model=NewsResponse)
async def get_top_headlines(
    query: Optional[str] = Query(None, description="Keywords to filter headlines"),
    category: Optional[str] = Query(
        "business",
        description="Category: business | entertainment | general | health | science | sports | technology",
    ),
    country: Optional[str] = Query("us", description="2-letter ISO 3166-1 country code, e.g. 'us'"),
    sources: Optional[str] = Query(
        None,
        description="Comma-separated NewsAPI source IDs. Cannot be combined with country/category.",
    ),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (1-100)"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """
    Get the latest top headlines.  
    Perfect for a daily market-briefing tool or AI agent morning update.

    - Defaults to the **business** category for equity use cases.
    - Set `sources` to pull from specific financial publishers (e.g. `bloomberg`, `reuters`).
    """
    try:
        data = await news_client.get_top_headlines(
            query=query,
            category=category,
            sources=sources,
            country=country,
            page_size=page_size,
            page=page,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# /news/market-pulse
# ─────────────────────────────────────────────

@router.get("/market-pulse", response_model=NewsResponse)
async def get_market_pulse(
    country: str = Query("us", description="2-letter country code"),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Shortcut to the top business/finance headlines – useful as a quick  
    market-pulse feed for an AI agent.
    """
    try:
        data = await news_client.get_market_headlines(country=country, page_size=page_size)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# /news/search
# ─────────────────────────────────────────────

@router.get("/search", response_model=NewsResponse)
async def search_articles(
    query: str = Query(..., description="Keywords / phrases. Supports AND, OR, NOT, quotes."),
    from_date: Optional[str] = Query(None, description="Start date: YYYY-MM-DD or ISO 8601"),
    to_date: Optional[str] = Query(None, description="End date: YYYY-MM-DD or ISO 8601"),
    language: str = Query("en", description="2-letter ISO-639-1 language code"),
    sort_by: str = Query(
        "publishedAt",
        description="Sort order: publishedAt | relevancy | popularity",
    ),
    sources: Optional[str] = Query(None, description="Comma-separated source IDs (max 20)"),
    domains: Optional[str] = Query(None, description="Restrict to these domains, e.g. 'reuters.com,ft.com'"),
    page_size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
):
    """
    Full-text search across all indexed articles.  
    Use rich query syntax: `"Apple" AND (earnings OR guidance)`.
    """
    try:
        data = await news_client.search_everything(
            query=query,
            from_date=from_date,
            to_date=to_date,
            language=language,
            sort_by=sort_by,
            sources=sources,
            domains=domains,
            page_size=page_size,
            page=page,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# /news/stock/{symbol}
# ─────────────────────────────────────────────

@router.get("/stock/{symbol}", response_model=StockNewsResponse)
async def get_stock_news(
    symbol: str = Path(..., description="Ticker symbol, e.g. AAPL"),
    company_name: Optional[str] = Query(None, description="Company name for broader matching, e.g. 'Apple'"),
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("publishedAt", description="publishedAt | relevancy | popularity"),
    sources: Optional[str] = Query(None, description="Comma-separated source IDs"),
):
    """
    Fetch financially-relevant news for a specific stock ticker.

    Internally builds a smart query:  
    `("AAPL" OR "Apple") AND (stock OR earnings OR analyst …)`  
    so the AI agent receives signal-rich articles only.
    """
    try:
        data = await news_client.get_stock_news(
            symbol=symbol.upper(),
            company_name=company_name,
            from_date=from_date,
            to_date=to_date,
            page_size=page_size,
            sort_by=sort_by,
            sources=sources,
        )
        articles = [NewsArticle(**a) for a in (data.get("articles") or [])]
        return StockNewsResponse(
            symbol=symbol.upper(),
            company_name=company_name,
            total_results=data.get("totalResults", len(articles)),
            articles=articles,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# /news/sector/{sector}
# ─────────────────────────────────────────────

@router.get("/sector/{sector}", response_model=NewsResponse)
async def get_sector_news(
    sector: str = Path(..., description="Sector keyword, e.g. 'technology', 'energy', 'healthcare'"),
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("publishedAt", description="publishedAt | relevancy | popularity"),
):
    """
    Get recent news for a market sector.  
    Useful for sector rotation analysis or thematic AI research.
    """
    try:
        data = await news_client.get_sector_news(
            sector=sector,
            from_date=from_date,
            to_date=to_date,
            page_size=page_size,
            sort_by=sort_by,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# /news/sentiment/{symbol}
# ─────────────────────────────────────────────

@router.get("/sentiment/{symbol}", response_model=SentimentNewsResponse)
async def get_sentiment_feed(
    symbol: str = Path(..., description="Ticker symbol, e.g. TSLA"),
    company_name: Optional[str] = Query(None, description="Company name for broader matching"),
    days_back: int = Query(7, ge=1, le=30, description="Calendar days of history (1-30)"),
    page_size: int = Query(30, ge=1, le=100, description="Number of articles"),
):
    """
    Return a sentiment-optimised article feed for a ticker.

    Articles are sorted by **relevancy** and filtered by financial keywords,
    ready to be piped into an LLM for sentiment scoring.  
    Each article exposes `title`, `description`, `content`, `source`, `url`,
    and `publishedAt` — the fields most useful for sentiment inference.
    """
    try:
        data = await news_client.get_sentiment_feed(
            symbol=symbol.upper(),
            company_name=company_name,
            days_back=days_back,
            page_size=page_size,
        )
        articles = [
            SentimentArticle(
                title=a.get("title"),
                description=a.get("description"),
                content=a.get("content"),
                source=a.get("source", {}).get("name") if a.get("source") else None,
                url=a.get("url"),
                publishedAt=a.get("publishedAt"),
            )
            for a in (data.get("articles") or [])
        ]
        return SentimentNewsResponse(
            symbol=symbol.upper(),
            total_results=data.get("totalResults", len(articles)),
            articles=articles,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# /news/sources
# ─────────────────────────────────────────────

@router.get("/sources", response_model=SourcesResponse)
async def get_news_sources(
    category: Optional[str] = Query(
        None,
        description="Filter by category: business | entertainment | general | health | science | sports | technology",
    ),
    language: Optional[str] = Query(None, description="2-letter ISO-639-1 language code, e.g. 'en'"),
    country: Optional[str] = Query(None, description="2-letter country code, e.g. 'us'"),
):
    """
    Discover available news publisher sources.  
    Use the returned `id` values in other endpoints' `sources` parameter.
    """
    try:
        data = await news_client.get_sources(
            category=category,
            language=language,
            country=country,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
