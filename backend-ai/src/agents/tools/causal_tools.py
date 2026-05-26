"""Causal intelligence tools for agents."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.services.causal_service import CausalService

logger = logging.getLogger(__name__)

_DB_SESSION: Optional[Session] = None


def _get_db() -> Session:
    """Get or create a shared DB session. Caller must close via _close_db()."""
    global _DB_SESSION
    if _DB_SESSION is None:
        from src.db.database import SessionLocal
        _DB_SESSION = SessionLocal()
    return _DB_SESSION


def _close_db():
    """Close the shared session if open."""
    global _DB_SESSION
    if _DB_SESSION is not None:
        _DB_SESSION.close()
        _DB_SESSION = None


def get_causal_tools():
    """Return list of causal intelligence tools."""
    return [
        get_commodity_price_summary,
        get_recent_geopolitical_events,
        get_classified_news_impact,
        get_portfolio_causal_analysis,
        get_market_hidden_patterns,
    ]


def get_commodity_price_summary(days: int = 7) -> dict[str, Any]:
    """Get summary of commodity price changes.

    Uses pre-computed deltas from ETL task when available (<1h old),
    falls back to real-time computation via CausalService.
    """
    from src.db.models import CommodityPrice

    db = _get_db()
    service = CausalService(db)

    try:
        # Attempt cache-first: check if a recent delta cache exists
        now = datetime.utcnow()
        cache_cutoff = now - timedelta(hours=1)

        # Use CausalService's unified delta logic
        changes = service.get_commodity_changes(days=days)

        # Enrich with name
        results = {}
        for symbol, data in changes.items():
            results[symbol] = {
                "current_price": data.get("current_price"),
                "change_pct": data.get("change_pct", 0),
                "direction": data.get("direction", "up"),
                "name": data.get("name", symbol),
            }

        return {"commodities": results, "days": days}

    except Exception:
        logger.exception("get_commodity_price_summary failed")
        return {"commodities": {}, "days": days, "error": str(Exception)}


def get_recent_geopolitical_events(hours: int = 48, min_confidence: float = 0.6) -> dict[str, Any]:
    """Get recent significant geopolitical events with pre-classified impacts.

    Impact classification is pre-computed during ETL (event_monitor_task), so
    this tool reads it directly instead of re-classifying at runtime.
    """
    from src.db.models import GeopoliticalEvent

    db = _get_db()

    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        events = (
            db.query(GeopoliticalEvent)
            .filter(
                GeopoliticalEvent.event_date >= cutoff,
                GeopoliticalEvent.confidence >= min_confidence,
            )
            .order_by(GeopoliticalEvent.event_date.desc())
            .limit(10)
            .all()
        )

        results = []
        for event in events:
            event_dict = {
                "title": event.title,
                "country": event.country,
                "category": event.category,
                "date": event.event_date.isoformat() if event.event_date else None,
                "confidence": event.confidence,
            }

            # Read pre-classified impact from raw_data (set during ETL)
            raw = event.raw_data or {}
            if "impact" in raw:
                event_dict["impact"] = raw["impact"]
            else:
                # Fallback for legacy events without pre-classification
                from src.integrations.event_impact_classifier import get_event_classifier
                classifier = get_event_classifier()
                impact = classifier.classify(event_dict)
                if impact:
                    event_dict["impact"] = {
                        "commodity": impact.commodity,
                        "direction": impact.direction,
                        "magnitude": impact.magnitude,
                        "affected_sectors": impact.affected_sectors,
                    }

            results.append(event_dict)

        return {"events": results, "count": len(results)}

    except Exception:
        logger.exception("get_recent_geopolitical_events failed")
        return {"events": [], "count": 0}


def get_classified_news_impact(limit: int = 10) -> dict[str, Any]:
    """Get recent news with commodity/sector impact."""
    from src.db.models import ClassifiedNews

    db = _get_db()

    try:
        cutoff = datetime.utcnow() - timedelta(hours=48)

        news = (
            db.query(ClassifiedNews)
            .filter(
                ClassifiedNews.published_at >= cutoff,
                ClassifiedNews.commodity.isnot(None) | ClassifiedNews.sector.isnot(None),
            )
            .order_by(ClassifiedNews.published_at.desc())
            .limit(limit)
            .all()
        )

        results = []
        for n in news:
            results.append({
                "title": n.title,
                "source": n.source,
                "commodity": n.commodity,
                "sector": n.sector,
                "impact_direction": n.impact_direction,
                "impact_type": n.impact_type,
                "confidence": n.classification_confidence,
            })

        return {"news": results, "count": len(results)}

    except Exception:
        logger.exception("get_classified_news_impact failed")
        return {"news": [], "count": 0}


def get_portfolio_causal_analysis(portfolio_id: str) -> dict[str, Any]:
    """Get causal analysis for a portfolio.

    Cache-first: reads from CausalInsight table (4h TTL),
    falls back to full computation on cache miss and saves result.
    """
    from src.db.models import CausalInsight

    db = _get_db()
    service = CausalService(db)

    try:
        pid = UUID(portfolio_id)

        # Step 1: Check cache
        cached = service.get_latest_insights(pid, hours=4)
        if cached:
            return {
                "portfolio_id": portfolio_id,
                "source": "cache",
                "insights": [
                    {
                        "title": ci.title,
                        "trigger": ci.trigger_event,
                        "commodity": ci.commodity,
                        "sector": ci.sector,
                        "impact_direction": ci.impact_direction,
                        "explanation": ci.explanation,
                        "recommendation": ci.recommendation,
                        "confidence": ci.confidence,
                    }
                    for ci in cached
                ],
            }

        # Step 2: Cache miss — compute fresh
        insights = service.analyze_portfolio(pid)

        if insights:
            service.save_insights(pid, insights)

        # Get supporting data for context
        commodity_data = get_commodity_price_summary(days=7)
        volatile_commodities = [
            k for k, v in commodity_data.get("commodities", {}).items()
            if abs(v.get("change_pct", 0)) >= 3
        ]

        return {
            "portfolio_id": portfolio_id,
            "source": "computed",
            "volatile_commodities": volatile_commodities,
            "insights": insights,
        }

    except Exception:
        logger.exception("get_portfolio_causal_analysis failed")
        return {"portfolio_id": portfolio_id, "error": "Failed to compute causal analysis"}


def get_market_hidden_patterns() -> dict[str, Any]:
    """Get currently hidden patterns in the market.

    Uses cached causal insights where available, supplements with
    commodity/event/news correlation at runtime.
    """
    from src.db.models import ClassifiedNews, GeopoliticalEvent

    db = _get_db()
    patterns = []

    try:
        # Get commodity changes via shared service
        service = CausalService(db)
        commodity_data = service.get_commodity_changes(days=7)

        # Pattern 1: Volatile commodities from pre-computed data
        for symbol, data in commodity_data.items():
            change_pct = data.get("change_pct", 0)
            if abs(change_pct) >= 4:
                patterns.append({
                    "pattern": "commodity_volatility",
                    "trigger": f"{data.get('name', symbol)} moved {change_pct:.1f}% in 7 days",
                    "direction": data.get("direction", "up"),
                    "sectors_affected": get_affected_sectors(symbol),
                    "confidence": min(0.85, 0.5 + abs(change_pct) / 20),
                })

        # Pattern 2: Sector momentum from news
        cutoff = datetime.utcnow() - timedelta(hours=48)
        news_items = (
            db.query(ClassifiedNews)
            .filter(ClassifiedNews.published_at >= cutoff)
            .all()
        )

        sector_sentiment: dict[str, dict[str, int]] = {}
        for n in news_items:
            sector = n.sector
            if sector:
                sector_sentiment.setdefault(sector, {"positive": 0, "negative": 0})
                if n.impact_direction == "positive":
                    sector_sentiment[sector]["positive"] += 1
                elif n.impact_direction == "negative":
                    sector_sentiment[sector]["negative"] += 1

        for sector, sentiment in sector_sentiment.items():
            total = sentiment["positive"] + sentiment["negative"]
            if total >= 2 and sentiment["positive"] >= sentiment["negative"]:
                patterns.append({
                    "pattern": "sector_bullish_news",
                    "trigger": f"{sector}: {sentiment['positive']} positive, {sentiment['negative']} negative news items",
                    "sectors_affected": [sector],
                    "confidence": 0.7,
                })

        return {
            "patterns": patterns,
            "count": len(patterns),
            "data_sources": {
                "commodities": len(commodity_data),
                "news": len(news_items),
            },
        }

    except Exception:
        logger.exception("get_market_hidden_patterns failed")
        return {"patterns": [], "count": 0}


def get_affected_sectors(commodity: str) -> list[str]:
    """Get sectors affected by a commodity."""
    from src.db.models import SectorExposure

    db = _get_db()
    try:
        exposures = (
            db.query(SectorExposure)
            .filter(
                SectorExposure.commodity == commodity,
                SectorExposure.is_active == True,
            )
            .all()
        )
        return [e.sector for e in exposures]
    except Exception:
        logger.exception("get_affected_sectors failed")
        return []


def close_causal_tools():
    """Close the shared DB session. Call after agent finishes."""
    _close_db()
