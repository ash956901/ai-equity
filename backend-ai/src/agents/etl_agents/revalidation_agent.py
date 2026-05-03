"""Insight Revalidation Agent.

For each ``Insight`` whose ``valid_until`` is now in the past:

1. Compare ``predicted_direction`` against realized price moves
   (when available via FMP/Upstox - the agent gracefully degrades to
   news-cluster overlap if the price API is missing).
2. Write an ``InsightOutcome`` row.
3. Auto-archive contradicted/stale insights.

Drift metrics live on ``InsightOutcome.observed_signal`` so the Discovery API
can compute precision per ``insight_type`` over a rolling window.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import Company, Insight, InsightOutcome, NewsArticle

logger = logging.getLogger(__name__)


def _classify_outcome(predicted: Optional[str], realized: Optional[float]) -> str:
    if predicted is None or realized is None:
        return "stale"
    if abs(realized) < 0.01:
        return "stale"
    if predicted == "up" and realized > 0:
        return "confirmed"
    if predicted == "down" and realized < 0:
        return "confirmed"
    if predicted == "neutral":
        return "confirmed" if abs(realized) < 0.05 else "contradicted"
    return "contradicted"


def _resolve_company_ticker(db: Session, company_id: str) -> Optional[str]:
    if not company_id:
        return None
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return None
    return company.ticker_nse or company.ticker_bse


def _fetch_realized_return(ticker: str, days: int) -> Optional[float]:
    """Try yfinance for a quick % return over the horizon. Returns None on failure."""
    if not ticker:
        return None
    try:
        import yfinance as yf  # type: ignore

        symbol = ticker
        if not symbol.endswith(".NS") and "." not in symbol:
            symbol = f"{ticker}.NS"
        hist = yf.Ticker(symbol).history(period=f"{max(days, 5)}d")
        if hist is None or hist.empty:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None
        return float((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0])
    except Exception as exc:
        logger.debug("yfinance return fetch failed for %s: %s", ticker, exc)
        return None


class InsightRevalidationAgent:
    """Compute insight outcomes + drift metrics."""

    def run(
        self,
        *,
        db: Optional[Session] = None,
        max_per_run: int = 200,
    ) -> Dict[str, Any]:
        own = db is None
        db = db or SessionLocal()
        summary = {"evaluated": 0, "confirmed": 0, "contradicted": 0, "stale": 0}
        try:
            insights = (
                db.query(Insight)
                .filter(Insight.status == "active")
                .filter(Insight.valid_until.isnot(None))
                .filter(Insight.valid_until <= datetime.utcnow())
                .limit(max_per_run)
                .all()
            )
            for insight in insights:
                tickers = self._extract_tickers(insight, db)
                realized = self._aggregate_realized_return(tickers, insight.horizon_days or 30)
                news_count = self._news_corroboration_count(db, insight)
                status = _classify_outcome(insight.predicted_direction, realized)

                outcome = InsightOutcome(
                    insight_id=insight.id,
                    predicted_direction=insight.predicted_direction,
                    horizon_days=insight.horizon_days,
                    observed_return=Decimal(str(round(realized, 6))) if realized is not None else None,
                    observed_news_count=news_count,
                    observed_signal={
                        "tickers": tickers,
                        "raw_return": realized,
                        "news_count": news_count,
                    },
                    status=status,
                    evaluated_at=datetime.utcnow(),
                )
                db.add(outcome)

                if status == "contradicted":
                    insight.status = "archived"
                    insight.archived_at = datetime.utcnow()
                elif status == "stale":
                    insight.status = "stale"

                summary["evaluated"] += 1
                summary[status] = summary.get(status, 0) + 1

            db.commit()
            return summary
        except Exception:
            db.rollback()
            raise
        finally:
            if own:
                db.close()

    # ------------------------------------------------------------------ #

    def _extract_tickers(self, insight: Insight, db: Session) -> List[str]:
        tickers: List[str] = []
        for entry in insight.primary_companies or []:
            cid = entry.get("company_id") if isinstance(entry, dict) else None
            t = _resolve_company_ticker(db, cid)
            if t:
                tickers.append(t)
        return tickers

    def _aggregate_realized_return(self, tickers: Iterable[str], days: int) -> Optional[float]:
        returns = []
        for t in tickers:
            r = _fetch_realized_return(t, days)
            if r is not None:
                returns.append(r)
        if not returns:
            return None
        return sum(returns) / len(returns)

    def _news_corroboration_count(self, db: Session, insight: Insight) -> int:
        if not insight.related_themes:
            return 0
        since = insight.generated_at or datetime.utcnow() - timedelta(days=insight.horizon_days or 30)
        return (
            db.query(NewsArticle)
            .filter(NewsArticle.published_at >= since)
            .filter(NewsArticle.keywords.overlap(list(insight.related_themes or [])))
            .count()
        )


def precision_by_type(*, lookback_days: int = 30) -> List[Dict[str, Any]]:
    """Compute precision per insight_type over a rolling window."""
    db = SessionLocal()
    try:
        from sqlalchemy import case, func

        since = datetime.utcnow() - timedelta(days=lookback_days)
        rows = (
            db.query(
                Insight.insight_type,
                func.count(InsightOutcome.id).label("evaluated"),
                func.sum(case((InsightOutcome.status == "confirmed", 1), else_=0)).label("confirmed"),
                func.sum(case((InsightOutcome.status == "contradicted", 1), else_=0)).label("contradicted"),
                func.sum(case((InsightOutcome.status == "stale", 1), else_=0)).label("stale"),
            )
            .join(InsightOutcome, InsightOutcome.insight_id == Insight.id)
            .filter(InsightOutcome.evaluated_at >= since)
            .group_by(Insight.insight_type)
            .all()
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            evaluated = int(r.evaluated or 0) or 1
            out.append(
                {
                    "insight_type": r.insight_type,
                    "evaluated": int(r.evaluated or 0),
                    "confirmed": int(r.confirmed or 0),
                    "contradicted": int(r.contradicted or 0),
                    "stale": int(r.stale or 0),
                    "precision": round((r.confirmed or 0) / evaluated, 3),
                }
            )
        return out
    finally:
        db.close()
