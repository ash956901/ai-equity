"""Social / alt-data ingestion pipeline.

Phase 1 priority sources are Reddit (public JSON endpoints, no key required
for read-only) and StockTwits. X/Twitter and Telegram are stubbed and gated
behind their respective tokens via the source registry.

Each post gets:
- sentiment polarity (positive/negative/neutral)
- stance (bullish/bearish/neutral/speculative)
- topic id (lightweight clustering placeholder; BERTopic optional plug-in)
- ticker extraction + company linkage where possible
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from src.db.database import SessionLocal
from src.db.models import Company, SocialPost, SocialTopic
from src.etl.guardrails import RateLimiter, is_source_disabled
from src.etl.sentiment import (
    classify_stance,
    extract_tickers,
    score_sentiment,
)
from src.etl.source_registry import get_source
from src.services.vector_service import VectorService

logger = logging.getLogger(__name__)

REDDIT_USER_AGENT = "EquityResearchBot/1.0 (by u/insight-engine)"


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #


def _build_universe_lookup(db) -> Dict[str, str]:
    rows = (
        db.query(Company)
        .filter(Company.listing_status == "active")
        .all()
    )
    lookup: Dict[str, str] = {}
    for c in rows:
        for t in (c.ticker_nse, c.ticker_bse):
            if t:
                lookup[t.upper()] = str(c.id)
    return lookup


def _ensure_topic(db, label: str) -> SocialTopic:
    existing = db.query(SocialTopic).filter(SocialTopic.label == label).first()
    if existing:
        return existing
    topic = SocialTopic(label=label, top_terms=[label.lower()], n_posts=0, is_active=True)
    db.add(topic)
    db.flush()
    return topic


def _classify_topic(text: str) -> str:
    """Lightweight topic classification.

    In production this is replaced by BERTopic; for the bootstrap we use a
    deterministic keyword bucket so the table populates without GPU time.
    """
    lowered = (text or "").lower()
    buckets = [
        ("Earnings", ("earnings", "results", "guidance", "ebitda", "profit")),
        ("M&A", ("merger", "acquisition", "buyout", "stake")),
        ("Regulation", ("sebi", "rbi", "regulatory", "ban", "fraud")),
        ("Macro & Commodity", ("rupee", "inflation", "crude", "brent", "fed", "rbi")),
        ("Tech & AI", ("ai", "data center", "gpu", "ml", "automation")),
        ("Energy & EV", ("ev", "electric vehicle", "lithium", "battery", "ethanol", "solar")),
        ("Pharma & Healthcare", ("pharma", "drug", "fda", "trial", "vaccine")),
        ("Banking & NBFC", ("bank", "nbfc", "loan", "deposit", "asset quality")),
    ]
    for label, terms in buckets:
        if any(t in lowered for t in terms):
            return label
    return "General"


def _persist_post(
    db,
    *,
    source: str,
    source_post_id: str,
    body: str,
    posted_at: datetime,
    author_handle: Optional[str],
    author_followers: Optional[int],
    raw: Dict[str, Any],
    universe: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    if not body or not body.strip():
        return None
    existing = (
        db.query(SocialPost)
        .filter(SocialPost.source == source, SocialPost.source_post_id == source_post_id)
        .first()
    )
    if existing:
        return None

    sentiment = score_sentiment(body)
    stance = classify_stance(body)
    tickers = extract_tickers(body, universe=set(universe.keys()))
    company_ids = [universe[t] for t in tickers if t in universe]

    topic_label = _classify_topic(body)
    topic = _ensure_topic(db, topic_label)
    topic.n_posts = (topic.n_posts or 0) + 1

    post = SocialPost(
        source=source,
        source_post_id=str(source_post_id),
        author_handle=author_handle,
        author_followers=author_followers,
        posted_at=posted_at,
        body=body[:8000],
        language="en",
        tickers=tickers or None,
        company_ids=company_ids or None,
        sentiment_label=sentiment["label"],
        sentiment_score=sentiment["score"],
        stance_label=stance,
        topic_id=topic.id,
        vector_id=str(uuid.uuid4()),
        raw=raw,
    )
    db.add(post)
    db.flush()
    return {
        "id": post.vector_id,
        "post_id": str(post.id),
        "source": source,
        "tickers": tickers,
        "company_ids": company_ids,
        "sentiment_label": post.sentiment_label,
        "stance_label": post.stance_label,
        "topic_id": str(topic.id),
        "posted_at": post.posted_at.isoformat() if post.posted_at else None,
        "body": post.body,
        "author_handle": post.author_handle,
        "author_followers": post.author_followers,
    }


# --------------------------------------------------------------------------- #
#  Reddit                                                                     #
# --------------------------------------------------------------------------- #


def _fetch_reddit(subreddits: List[str], per_sub_limit: int = 25) -> List[Dict[str, Any]]:
    cfg = get_source("social", "reddit") or {}
    limiter = RateLimiter("reddit", rpm=int(cfg.get("quota_rpm", 60)))
    out: List[Dict[str, Any]] = []
    for sub in subreddits:
        if not limiter.acquire(timeout=5.0):
            continue
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/new.json",
                params={"limit": per_sub_limit},
                headers={"User-Agent": REDDIT_USER_AGENT},
                timeout=15,
            )
        except Exception as exc:
            logger.debug("Reddit fetch failed for %s: %s", sub, exc)
            continue
        if resp.status_code != 200:
            continue
        children = ((resp.json() or {}).get("data") or {}).get("children") or []
        for child in children:
            data = child.get("data") or {}
            text = (data.get("title") or "") + "\n" + (data.get("selftext") or "")
            posted = datetime.fromtimestamp(data.get("created_utc", 0), tz=timezone.utc)
            out.append(
                {
                    "source": "reddit",
                    "source_post_id": data.get("id"),
                    "body": text,
                    "posted_at": posted,
                    "author_handle": data.get("author"),
                    "author_followers": None,
                    "raw": {
                        "subreddit": data.get("subreddit"),
                        "permalink": data.get("permalink"),
                        "score": data.get("score"),
                    },
                }
            )
        time.sleep(0.5)
    return out


# --------------------------------------------------------------------------- #
#  StockTwits                                                                 #
# --------------------------------------------------------------------------- #


def _fetch_stocktwits(tickers: List[str], per_ticker_limit: int = 20) -> List[Dict[str, Any]]:
    cfg = get_source("social", "stocktwits") or {}
    limiter = RateLimiter("stocktwits", rpm=int(cfg.get("quota_rpm", 30)))
    out: List[Dict[str, Any]] = []
    for ticker in tickers[:50]:
        if not limiter.acquire(timeout=5.0):
            continue
        try:
            resp = requests.get(
                f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json",
                timeout=15,
            )
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        messages = (resp.json() or {}).get("messages") or []
        for m in messages[:per_ticker_limit]:
            posted = m.get("created_at")
            try:
                ts = datetime.fromisoformat(posted.replace("Z", "+00:00")) if posted else datetime.now(timezone.utc)
            except Exception:
                ts = datetime.now(timezone.utc)
            out.append(
                {
                    "source": "stocktwits",
                    "source_post_id": m.get("id"),
                    "body": m.get("body") or "",
                    "posted_at": ts,
                    "author_handle": ((m.get("user") or {}).get("username")),
                    "author_followers": ((m.get("user") or {}).get("followers")),
                    "raw": {"ticker": ticker, "entities": m.get("entities")},
                }
            )
    return out


# --------------------------------------------------------------------------- #
#  Public API                                                                 #
# --------------------------------------------------------------------------- #


def ingest_social(
    *,
    portfolio_only: bool = False,
    portfolio_tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run a single ingestion sweep across enabled sources."""
    db = SessionLocal()
    summary = {"reddit": 0, "stocktwits": 0, "twitter": 0, "telegram": 0, "indexed": 0}
    try:
        universe = _build_universe_lookup(db)

        all_indexable: List[Dict[str, Any]] = []
        reddit_cfg = get_source("social", "reddit") or {}
        if reddit_cfg and not is_source_disabled("reddit"):
            subs = reddit_cfg.get("subreddits") or [
                "IndianStockMarket",
                "IndianStreetBets",
                "StocksAndTrading",
            ]
            for raw in _fetch_reddit(subs, per_sub_limit=15):
                rec = _persist_post(
                    db,
                    source="reddit",
                    source_post_id=raw["source_post_id"],
                    body=raw["body"],
                    posted_at=raw["posted_at"],
                    author_handle=raw["author_handle"],
                    author_followers=raw["author_followers"],
                    raw=raw["raw"],
                    universe=universe,
                )
                if rec:
                    summary["reddit"] += 1
                    all_indexable.append(rec)

        stocktwits_cfg = get_source("social", "stocktwits") or {}
        if stocktwits_cfg and not is_source_disabled("stocktwits"):
            tickers = portfolio_tickers or list(universe.keys())[:25]
            for raw in _fetch_stocktwits(tickers, per_ticker_limit=10):
                rec = _persist_post(
                    db,
                    source="stocktwits",
                    source_post_id=raw["source_post_id"],
                    body=raw["body"],
                    posted_at=raw["posted_at"],
                    author_handle=raw["author_handle"],
                    author_followers=raw["author_followers"],
                    raw=raw["raw"],
                    universe=universe,
                )
                if rec:
                    summary["stocktwits"] += 1
                    all_indexable.append(rec)

        # Twitter / Telegram intentionally gated; emit a structured record so
        # operators see them in ETLRun metadata.
        if get_source("social", "twitter") and not os.getenv("TWITTER_BEARER_TOKEN"):
            logger.info("twitter source enabled but TWITTER_BEARER_TOKEN missing")
        if get_source("social", "telegram") and not os.getenv("TELEGRAM_BOT_TOKEN"):
            logger.info("telegram source enabled but TELEGRAM_BOT_TOKEN missing")

        db.commit()

        if all_indexable:
            summary["indexed"] = VectorService().index_social_posts(all_indexable)

        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reap_deleted_posts(retention_days: int = 30) -> int:
    """Reaper job: blanks bodies of posts older than retention_days that
    we suspect were deleted upstream. Phase 1 keeps this conservative -
    we just stamp ``deleted_upstream_at`` on social_posts beyond the window.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow().timestamp() - retention_days * 86400
        from datetime import datetime as _dt

        cutoff_dt = _dt.utcfromtimestamp(cutoff)
        posts = (
            db.query(SocialPost)
            .filter(
                SocialPost.deleted_upstream_at.is_(None),
                SocialPost.posted_at < cutoff_dt,
            )
            .limit(500)
            .all()
        )
        for p in posts:
            p.deleted_upstream_at = _dt.utcnow()
            p.body = ""
        db.commit()
        return len(posts)
    finally:
        db.close()
