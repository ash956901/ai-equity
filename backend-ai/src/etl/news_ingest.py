"""News ingestion pipeline.

Fetches articles from configured sources (NewsAPI, NewsData.io, Google News
RSS), deduplicates by ``source_url``, persists ``news_articles`` rows with
sentiment metadata, and indexes them into Qdrant ``news_articles``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

from src.config import get_settings
from src.db.database import SessionLocal
from src.db.models import Company, NewsArticle
from src.etl.guardrails import RateLimiter, is_source_disabled
from src.etl.sentiment import (
    classify_stance,
    detect_affected_dimension,
    detect_impact_level,
    extract_tickers,
    score_sentiment,
)
from src.etl.source_registry import get_source
from src.services.vector_service import VectorService

logger = logging.getLogger(__name__)


def _parse_published(raw: Optional[str]) -> datetime:
    if not raw:
        return datetime.utcnow()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(raw)
    except Exception:
        return datetime.utcnow()


# --------------------------------------------------------------------------- #
#  Source-specific fetchers                                                   #
# --------------------------------------------------------------------------- #


def _fetch_newsapi(query: str, since: datetime, limit: int = 30) -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.news_api_key:
        return []
    cfg = get_source("news", "newsapi") or {}
    limiter = RateLimiter("newsapi", rpm=int(cfg.get("quota_rpm", 30)))
    if not limiter.acquire(timeout=5.0):
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": since.strftime("%Y-%m-%d"),
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": limit,
            },
            headers={"X-Api-Key": settings.news_api_key},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("articles", []) or []
    except Exception as exc:
        logger.debug("NewsAPI fetch failed: %s", exc)
        return []


def _fetch_newsdata(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.newsdata_api_key:
        return []
    cfg = get_source("news", "newsdata_io") or {}
    limiter = RateLimiter("newsdata_io", rpm=int(cfg.get("quota_rpm", 20)))
    if not limiter.acquire(timeout=5.0):
        return []
    try:
        resp = requests.get(
            "https://newsdata.io/api/1/news",
            params={
                "apikey": settings.newsdata_api_key,
                "q": query,
                "language": "en",
                "country": "in",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("results", []) or []
    except Exception as exc:
        logger.debug("NewsDataIO fetch failed: %s", exc)
        return []


def _fetch_google_rss(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    cfg = get_source("news", "google_news_rss") or {}
    limiter = RateLimiter("google_news_rss", rpm=int(cfg.get("quota_rpm", 60)))
    if not limiter.acquire(timeout=5.0):
        return []
    try:
        import feedparser  # type: ignore
    except ImportError:
        return []
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        logger.debug("Google RSS fetch failed: %s", exc)
        return []
    out: List[Dict[str, Any]] = []
    for entry in feed.entries[:limit]:
        out.append(
            {
                "title": entry.get("title"),
                "description": entry.get("summary"),
                "url": entry.get("link"),
                "source": (entry.get("source") or {}).get("title", "Google News"),
                "publishedAt": entry.get("published"),
            }
        )
    return out


# --------------------------------------------------------------------------- #
#  Normalization + persistence                                                #
# --------------------------------------------------------------------------- #


def _normalize_article(raw: Dict[str, Any], source_label: str) -> Optional[Dict[str, Any]]:
    headline = raw.get("title") or raw.get("headline")
    url = raw.get("url") or raw.get("link") or raw.get("source_url")
    if not headline or not url:
        return None
    body = raw.get("description") or raw.get("content") or raw.get("body") or ""
    source = raw.get("source")
    if isinstance(source, dict):
        source = source.get("name") or source_label
    elif not source:
        source = source_label
    published = _parse_published(raw.get("publishedAt") or raw.get("pubDate") or raw.get("published_at"))
    return {
        "headline": headline.strip(),
        "body": body.strip() if body else "",
        "source": source,
        "source_url": url,
        "published_at": published,
    }


def _persist_articles(
    db,
    universe: set,
    company_lookup: Dict[str, str],
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    persisted: List[Dict[str, Any]] = []
    for art in articles:
        existing = (
            db.query(NewsArticle)
            .filter(NewsArticle.source_url == art["source_url"])
            .first()
        )
        if existing:
            continue
        full_text = f"{art['headline']}. {art.get('body','')}"
        sentiment = score_sentiment(full_text)
        tickers = extract_tickers(full_text, universe=universe)
        company_id = None
        for t in tickers:
            if t in company_lookup:
                company_id = company_lookup[t]
                break
        impact = detect_impact_level(full_text)
        dimension = detect_affected_dimension(full_text)

        row = NewsArticle(
            company_id=company_id,
            headline=art["headline"][:5000],
            body=art.get("body") or "",
            source=art.get("source"),
            source_url=art["source_url"],
            published_at=art["published_at"],
            sentiment_score=sentiment["score"],
            sentiment_label=sentiment["label"],
            impact_level=impact,
            relevance_confidence=0.6 if company_id else 0.3,
            affected_dimension=dimension,
            tickers=tickers or None,
        )
        db.add(row)
        db.flush()
        persisted.append(
            {
                "id": str(row.id),
                "company_id": str(company_id) if company_id else None,
                "headline": row.headline,
                "body": row.body,
                "source": row.source,
                "source_url": row.source_url,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "tickers": tickers,
                "themes": [],
            }
        )
    return persisted


# --------------------------------------------------------------------------- #
#  Public API                                                                 #
# --------------------------------------------------------------------------- #


def ingest_news_for_universe(
    *,
    company_ids: Optional[List[str]] = None,
    days: int = 1,
    per_company_limit: int = 5,
) -> Dict[str, int]:
    """Ingest news for the given list of company UUIDs, or for the watchlist
    when ``company_ids`` is None. Hourly runs should pass ``days=1``.
    """
    db = SessionLocal()
    summary = {"fetched": 0, "stored": 0, "indexed": 0, "skipped_disabled": 0}
    try:
        query = db.query(Company).filter(Company.listing_status == "active")
        if company_ids:
            query = query.filter(Company.id.in_(company_ids))
        else:
            query = query.limit(200)
        companies = query.all()

        universe = set()
        company_lookup: Dict[str, str] = {}
        for c in companies:
            for t in (c.ticker_nse, c.ticker_bse):
                if t:
                    universe.add(t)
                    company_lookup[t] = str(c.id)

        all_articles: List[Dict[str, Any]] = []
        since = datetime.utcnow() - timedelta(days=days)
        for c in companies:
            queries = [c.name]
            if c.ticker_nse:
                queries.append(f"{c.ticker_nse} stock")
            collected: List[Dict[str, Any]] = []
            for q in queries:
                if not is_source_disabled("newsapi"):
                    collected.extend(
                        n
                        for raw in _fetch_newsapi(q, since, per_company_limit)
                        for n in [_normalize_article(raw, "NewsAPI")]
                        if n
                    )
                else:
                    summary["skipped_disabled"] += 1
                if not is_source_disabled("newsdata_io"):
                    collected.extend(
                        n
                        for raw in _fetch_newsdata(q, per_company_limit)
                        for n in [_normalize_article(raw, "NewsData.io")]
                        if n
                    )
                if not is_source_disabled("google_news_rss"):
                    collected.extend(
                        n
                        for raw in _fetch_google_rss(q, per_company_limit)
                        for n in [_normalize_article(raw, "Google News")]
                        if n
                    )
            all_articles.extend(collected)
        summary["fetched"] = len(all_articles)

        # Deduplicate by URL within this batch before persisting
        seen_urls = set()
        unique_articles: List[Dict[str, Any]] = []
        for a in all_articles:
            if a["source_url"] in seen_urls:
                continue
            seen_urls.add(a["source_url"])
            unique_articles.append(a)

        persisted = _persist_articles(db, universe, company_lookup, unique_articles)
        db.commit()
        summary["stored"] = len(persisted)

        if persisted:
            summary["indexed"] = VectorService().index_news(persisted)

        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
