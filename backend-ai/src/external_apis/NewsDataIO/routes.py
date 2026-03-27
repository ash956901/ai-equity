"""
FastAPI routes for NewsData.io endpoints.
Prefix: /newsdata
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional

from .client import NewsDataIOClient
from .models import (
    NewsDataResponse,
    NewsDataSourcesResponse,
    NewsDataCountResponse,
    TickerNewsResponse,
    SentimentFeedResponse,
    SentimentFeedArticle,
    NewsDataArticle,
)

router = APIRouter(prefix="/newsdata", tags=["NewsData.io API"])
client = NewsDataIOClient()


def _handle_newsdata_error(e: Exception):
    """Convert NewsData errors to appropriate HTTP responses."""
    if isinstance(e, ValueError):
        raise HTTPException(status_code=503, detail=str(e))
    raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# /newsdata/latest
# ─────────────────────────────────────────────

@router.get("/latest", response_model=NewsDataResponse)
async def get_latest_news(
    query: Optional[str] = Query(None, description="Keywords. Supports AND/OR/NOT, quotes."),
    query_in_title: Optional[str] = Query(None, description="Keywords restricted to article titles."),
    timeframe: Optional[str] = Query(None, description="Recent window: hours '6' or minutes '30m'. Max 48 h / 2880 m."),
    country: Optional[str] = Query(None, description="Comma-separated 2-letter country codes, e.g. 'us,gb'."),
    category: Optional[str] = Query("business,top", description="Comma-separated categories: business, top, science, technology, etc."),
    language: Optional[str] = Query("en", description="Comma-separated 2-letter language codes."),
    domain: Optional[str] = Query(None, description="Comma-separated NewsData.io domain IDs."),
    domainurl: Optional[str] = Query(None, description="Comma-separated domain URLs, e.g. 'ft.com,wsj.com'."),
    prioritydomain: Optional[str] = Query("top", description="Domain quality: top | medium | low."),
    datatype: Optional[str] = Query(None, description="Article type: news, blog, press_release, research, etc."),
    full_content: Optional[int] = Query(None, description="1 = only articles with full content."),
    image: Optional[int] = Query(None, description="1 = only articles with images."),
    removeduplicate: int = Query(1, description="1 = remove duplicate articles."),
    size: int = Query(10, ge=1, le=50, description="Articles per request (1–50; free tier max 10)."),
    page: Optional[str] = Query(None, description="nextPage token for pagination."),
):
    """
    Fetch breaking news from the past 48 hours.  
    Defaults to **business + top** category from high-priority English sources.
    """
    try:
        data = await client.get_latest(
            query=query,
            query_in_title=query_in_title,
            timeframe=timeframe,
            country=country,
            category=category,
            language=language,
            domain=domain,
            domainurl=domainurl,
            prioritydomain=prioritydomain,
            datatype=datatype,
            full_content=full_content,
            image=image,
            removeduplicate=removeduplicate,
            size=size,
            page=page,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/market
# ─────────────────────────────────────────────

@router.get("/market", response_model=NewsDataResponse)
async def get_market_news(
    query: Optional[str] = Query(None, description="Keyword search across title, content, and meta."),
    query_in_title: Optional[str] = Query(None, description="Keywords restricted to titles."),
    symbol: Optional[str] = Query(None, description="Stock ticker(s), e.g. 'AAPL' or 'AAPL,TSLA,MSFT'."),
    timeframe: Optional[str] = Query(None, description="Recent window: hours '6' or minutes '30m'."),
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD."),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD."),
    country: Optional[str] = Query(None, description="Comma-separated country codes."),
    language: Optional[str] = Query("en", description="Comma-separated language codes."),
    domain: Optional[str] = Query(None, description="Domain IDs."),
    domainurl: Optional[str] = Query(None, description="Domain URLs."),
    prioritydomain: Optional[str] = Query(None, description="top | medium | low."),
    sentiment: Optional[str] = Query(None, description="positive | negative | neutral (Pro/Corporate plans only)."),
    sort: Optional[str] = Query("relevancy", description="pubdateasc | relevancy | source | fetched_at."),
    full_content: Optional[int] = Query(None, description="1 = full content only."),
    image: Optional[int] = Query(None, description="1 = articles with images only."),
    removeduplicate: int = Query(1, description="1 to remove duplicates."),
    size: int = Query(10, ge=1, le=50),
    page: Optional[str] = Query(None, description="nextPage token."),
):
    """
    Curated financial and market news.  
    The `symbol` parameter is the most powerful feature – it filters news
    by stock ticker directly (e.g. `symbol=AAPL,TSLA`).

    Returns earnings releases, analyst notes, macro events, and company headlines.
    """
    try:
        data = await client.get_market_news(
            query=query,
            query_in_title=query_in_title,
            symbol=symbol.upper() if symbol else None,
            timeframe=timeframe,
            from_date=from_date,
            to_date=to_date,
            country=country,
            language=language,
            domain=domain,
            domainurl=domainurl,
            prioritydomain=prioritydomain,
            sentiment=sentiment,
            sort=sort,
            full_content=full_content,
            image=image,
            removeduplicate=removeduplicate,
            size=size,
            page=page,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/ticker/{symbol}
# ─────────────────────────────────────────────

@router.get("/ticker/{symbol}", response_model=TickerNewsResponse)
async def get_ticker_news(
    symbol: str = Path(..., description="Stock ticker, e.g. AAPL"),
    timeframe: Optional[str] = Query(None, description="Recent window: hours '6' or minutes '30m'."),
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD."),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD."),
    language: str = Query("en"),
    sentiment: Optional[str] = Query(None, description="positive | negative | neutral (Pro+ only)."),
    prioritydomain: str = Query("top", description="top | medium | low."),
    size: int = Query(20, ge=1, le=50),
    page: Optional[str] = Query(None, description="nextPage token."),
):
    """
    Ticker-specific market news using NewsData.io's native ``symbol`` filter.  
    More precise than keyword search – maps directly to the stock ticker.
    """
    try:
        data = await client.get_ticker_news(
            symbol=symbol.upper(),
            timeframe=timeframe,
            from_date=from_date,
            to_date=to_date,
            language=language,
            sentiment=sentiment,
            prioritydomain=prioritydomain,
            size=size,
            page=page,
        )
        articles = [NewsDataArticle(**a) for a in (data.get("results") or [])]
        return TickerNewsResponse(
            symbol=symbol.upper(),
            total_results=data.get("totalResults", len(articles)),
            articles=articles,
            next_page=data.get("nextPage"),
        )
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/sentiment/{symbol}
# ─────────────────────────────────────────────

@router.get("/sentiment/{symbol}", response_model=SentimentFeedResponse)
async def get_sentiment_feed(
    symbol: str = Path(..., description="Stock ticker, e.g. NVDA"),
    hours_back: int = Query(24, ge=1, le=48, description="Hours of history (1–48)."),
    size: int = Query(30, ge=1, le=50, description="Number of articles."),
    language: str = Query("en"),
):
    """
    Relevancy-sorted, deduplicated market news feed for an LLM sentiment scorer.

    Returns `title`, `description`, `content`, `ai_summary`, `sentiment`
    (and `sentiment_stats`) when available from your NewsData.io plan.  
    On free/basic plans, pipe `title + description + content` into your own LLM.
    """
    try:
        data = await client.get_market_sentiment_feed(
            symbol=symbol.upper(),
            hours_back=hours_back,
            size=size,
            language=language,
        )
        articles = [
            SentimentFeedArticle(
                article_id=a.get("article_id"),
                title=a.get("title"),
                description=a.get("description"),
                content=a.get("content"),
                source_name=a.get("source_name"),
                link=a.get("link"),
                pubDate=a.get("pubDate"),
                sentiment=a.get("sentiment"),
                sentiment_stats=a.get("sentiment_stats"),
                ai_summary=a.get("ai_summary"),
            )
            for a in (data.get("results") or [])
        ]
        return SentimentFeedResponse(
            symbol=symbol.upper(),
            total_results=data.get("totalResults", len(articles)),
            articles=articles,
            next_page=data.get("nextPage"),
        )
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/crypto
# ─────────────────────────────────────────────

@router.get("/crypto", response_model=NewsDataResponse)
async def get_crypto_news(
    query: Optional[str] = Query(None, description="Keyword search."),
    coin: Optional[str] = Query(None, description="Comma-separated coin tickers, e.g. 'btc,eth,sol'."),
    timeframe: Optional[str] = Query(None, description="Recent window: hours '6' or minutes '30m'."),
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD."),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD."),
    language: Optional[str] = Query("en"),
    sentiment: Optional[str] = Query(None, description="positive | negative | neutral (Pro+ only)."),
    sort: Optional[str] = Query("relevancy"),
    full_content: Optional[int] = Query(None),
    removeduplicate: int = Query(1),
    size: int = Query(10, ge=1, le=50),
    page: Optional[str] = Query(None),
):
    """
    Cryptocurrency-focused news with optional coin-symbol filtering.  
    Useful for tracking crypto exposure of equities (exchanges, miners, ETFs).
    """
    try:
        data = await client.get_crypto_news(
            query=query,
            coin=coin,
            timeframe=timeframe,
            from_date=from_date,
            to_date=to_date,
            language=language,
            sentiment=sentiment,
            sort=sort,
            full_content=full_content,
            removeduplicate=removeduplicate,
            size=size,
            page=page,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/market/headlines  (shortcut)
# ─────────────────────────────────────────────

@router.get("/market/headlines", response_model=NewsDataResponse)
async def get_financial_headlines(
    country: str = Query("us", description="Country code."),
    timeframe: Optional[str] = Query(None, description="Recent window in hours (1–48). Requires paid plan."),
    prioritydomain: str = Query("top", description="top | medium | low."),
    size: int = Query(20, ge=1, le=50),
):
    """
    Top financial headlines from premium sources – daily market briefing feed.  
    Defaults to the last 6 hours from top-tier US financial publishers.
    """
    try:
        data = await client.get_financial_headlines(
            country=country,
            timeframe=timeframe,
            prioritydomain=prioritydomain,
            size=size,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/earnings
# ─────────────────────────────────────────────

@router.get("/earnings", response_model=NewsDataResponse)
async def get_earnings_news(
    symbol: Optional[str] = Query(None, description="Optional ticker(s), e.g. 'AAPL'. Omit for broad earnings feed."),
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD."),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD."),
    language: str = Query("en"),
    size: int = Query(20, ge=1, le=50),
):
    """
    Earnings-focused market news: EPS beats/misses, revenue guidance,
    analyst reactions, and quarterly results.

    Combine with `symbol` to get ticker-specific earnings coverage.
    """
    try:
        data = await client.get_earnings_news(
            symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            language=language,
            size=size,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/archive  (paid plans only)
# ─────────────────────────────────────────────

@router.get("/archive", response_model=NewsDataResponse)
async def get_archive(
    from_date: str = Query(..., description="Required start date YYYY-MM-DD."),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD; defaults to today."),
    query: Optional[str] = Query(None, description="Keyword search."),
    country: Optional[str] = Query(None),
    category: Optional[str] = Query(None, description="e.g. 'business,top'"),
    language: Optional[str] = Query("en"),
    domain: Optional[str] = Query(None),
    domainurl: Optional[str] = Query(None),
    prioritydomain: Optional[str] = Query(None),
    sort: Optional[str] = Query("relevancy"),
    full_content: Optional[int] = Query(None),
    image: Optional[int] = Query(None),
    removeduplicate: int = Query(1),
    size: int = Query(10, ge=1, le=50),
    page: Optional[str] = Query(None),
):
    """
    Historical news archive (**paid plans only – costs 5 credits per request**).

    Date coverage: Basic = 6 months, Professional = 2 years, Corporate = 5 years.  
    Must supply at least one filter alongside `from_date`:
    `query`, `country`, `category`, `language`, `domain`, etc.
    """
    try:
        data = await client.get_archive(
            from_date=from_date,
            to_date=to_date,
            query=query,
            country=country,
            category=category,
            language=language,
            domain=domain,
            domainurl=domainurl,
            prioritydomain=prioritydomain,
            sort=sort,
            full_content=full_content,
            image=image,
            removeduplicate=removeduplicate,
            size=size,
            page=page,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/sources
# ─────────────────────────────────────────────

@router.get("/sources", response_model=NewsDataSourcesResponse)
async def get_sources(
    language: Optional[str] = Query(None, description="Language code, e.g. 'en'."),
    country: Optional[str] = Query(None, description="Country code, e.g. 'us'."),
    category: Optional[str] = Query(None, description="Category filter."),
    domainurl: Optional[str] = Query(None, description="Specific domain URL lookup."),
    prioritydomain: Optional[str] = Query(None, description="top | medium | low."),
):
    """
    List available news publisher domains (up to 100, randomly sampled).  
    Use the returned `id` values in the `domain` parameter of other endpoints.
    """
    try:
        data = await client.get_sources(
            language=language,
            country=country,
            category=category,
            domainurl=domainurl,
            prioritydomain=prioritydomain,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)


# ─────────────────────────────────────────────
# /newsdata/count  (paid plans only)
# ─────────────────────────────────────────────

@router.get("/count", response_model=NewsDataCountResponse)
async def get_article_count(
    from_date: str = Query(..., description="Required start date YYYY-MM-DD."),
    to_date: str = Query(..., description="Required end date YYYY-MM-DD."),
    endpoint: str = Query("market", description="archive | crypto | market."),
    interval: Optional[str] = Query("day", description="all | day | hour."),
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None, description="Ticker(s) – market endpoint only."),
    coin: Optional[str] = Query(None, description="Coin(s) – crypto endpoint only."),
):
    """
    Get article volume counts without fetching content (**paid; 50 credits per request**).

    Useful for: understanding coverage density, validating data before archiving,
    or monitoring news velocity around a ticker/event.
    """
    try:
        data = await client.get_count(
            from_date=from_date,
            to_date=to_date,
            endpoint=endpoint,
            interval=interval,
            query=query,
            category=category,
            country=country,
            language=language,
            symbol=symbol,
            coin=coin,
        )
        return data
    except Exception as e:
        _handle_newsdata_error(e)
