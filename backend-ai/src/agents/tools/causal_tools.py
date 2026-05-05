"""Causal intelligence tools for agents."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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
    
    Returns:
        Dict with commodity symbol -> {price, change_pct, direction}
    """
    from src.db.database import SessionLocal
    from src.db.models import CommodityPrice
    
    db = SessionLocal()
    results = {}
    
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        symbols = db.query(CommodityPrice.symbol).distinct().all()
        symbols = [s[0] for s in symbols]
        
        for symbol in symbols:
            latest = (
                db.query(CommodityPrice)
                .filter(CommodityPrice.symbol == symbol)
                .order_by(CommodityPrice.timestamp.desc())
                .first()
            )
            
            old_price = (
                db.query(CommodityPrice)
                .filter(
                    CommodityPrice.symbol == symbol,
                    CommodityPrice.timestamp <= cutoff,
                )
                .order_by(CommodityPrice.timestamp.desc())
                .first()
            )
            
            if latest and old_price and old_price.price:
                change_pct = ((latest.price - old_price.price) / old_price.price) * 100
                results[symbol] = {
                    "current_price": latest.price,
                    "change_pct": round(change_pct, 2),
                    "direction": "up" if change_pct > 0 else "down",
                    "name": latest.name,
                }
        
        return {"commodities": results, "days": days}
        
    finally:
        db.close()


def get_recent_geopolitical_events(hours: int = 48, min_confidence: float = 0.6) -> dict[str, Any]:
    """Get recent significant geopolitical events.
    
    Returns:
        List of events with impact classification
    """
    from src.db.database import SessionLocal
    from src.db.models import GeopoliticalEvent
    from src.integrations.event_impact_classifier import get_event_classifier
    
    db = SessionLocal()
    classifier = get_event_classifier()
    
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
            
            # Get impact
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
        
    finally:
        db.close()


def get_classified_news_impact(limit: int = 10) -> dict[str, Any]:
    """Get recent news with commodity/sector impact.
    
    Returns:
        List of news articles with supply/demand impact
    """
    from src.db.database import SessionLocal
    from src.db.models import ClassifiedNews
    
    db = SessionLocal()
    
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
        
    finally:
        db.close()


def get_portfolio_causal_analysis(portfolio_id: str) -> dict[str, Any]:
    """Get causal analysis for a portfolio.
    
    Returns:
        Analysis connecting commodities, events, and news to holdings
    """
    from uuid import UUID
    
    from src.db.database import SessionLocal
    from src.db.models import Company, Holding, Portfolio
    from src.services.causal_service import CausalService
    
    db = SessionLocal()
    
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.id == UUID(portfolio_id)).first()
        if not portfolio:
            return {"error": "Portfolio not found"}
        
        holdings = (
            db.query(Holding)
            .filter(Holding.portfolio_id == UUID(portfolio_id))
            .all()
        )
        
        # Get commodity changes
        commodity_data = get_commodity_price_summary(days=7)
        volatile_commodities = [
            k for k, v in commodity_data.get("commodities", {}).items()
            if abs(v.get("change_pct", 0)) >= 3
        ]
        
        # Get events
        events_data = get_recent_geopolitical_events(hours=48)
        significant_events = [
            e for e in events_data.get("events", [])
            if e.get("impact", {}).get("commodity")
        ]
        
        # Get news
        news_data = get_classified_news_impact()
        
        # Build analysis
        analysis = {
            "portfolio_id": portfolio_id,
            "holdings_count": len(holdings),
            "volatile_commodities": volatile_commodities,
            "significant_events_count": len(significant_events),
            "impactful_news_count": news_data.get("count", 0),
            "patterns": [],
        }
        
        # Identify patterns
        for holding in holdings:
            company = db.query(Company).filter(Company.id == holding.company_id).first()
            if not company or not company.sector:
                continue
            
            sector = company.sector
            patterns = []
            
            # Check commodity exposure
            for comm, data in commodity_data.get("commodities", {}).items():
                if abs(data.get("change_pct", 0)) >= 3:
                    patterns.append({
                        "type": "commodity",
                        "trigger": f"{comm} {data.get('direction')} {data.get('change_pct')}%",
                        "sector": sector,
                        "company": company.name,
                        "confidence": 0.7,
                    })
            
            # Check news impact
            for news_item in news_data.get("news", []):
                if news_item.get("sector") == sector:
                    patterns.append({
                        "type": "news",
                        "trigger": news_item.get("title", "")[:50],
                        "direction": news_item.get("impact_direction"),
                        "sector": sector,
                        "company": company.name,
                        "confidence": news_item.get("confidence", 0.5),
                    })
            
            if patterns:
                analysis["patterns"].extend(patterns)
        
        return analysis
        
    finally:
        db.close()


def get_market_hidden_patterns() -> dict[str, Any]:
    """Get currently hidden patterns in the market.
    
    Returns:
        Hidden patterns detected from all data sources
    """
    from src.db.database import SessionLocal
    
    db = SessionLocal()
    patterns = []
    
    try:
        # Get all three data sources
        commodity_data = get_commodity_price_summary(days=7)
        events_data = get_recent_geopolitical_events(hours=72)
        news_data = get_classified_news_impact()
        
        # Pattern 1: Volatile commodities with event correlation
        for comm, data in commodity_data.get("commodities", {}).items():
            if abs(data.get("change_pct", 0)) >= 4:
                # Check for related events
                related_events = [
                    e for e in events_data.get("events", [])
                    if e.get("impact", {}).get("commodity") == comm
                ]
                if related_events:
                    patterns.append({
                        "pattern": "event_driven_commodity",
                        "trigger": f"{comm} moved {data.get('change_pct')}%",
                        "cause": related_events[0].get("title", "")[:60],
                        "sectors_affected": get_affected_sectors(comm),
                        "confidence": 0.8,
                    })
        
        # Pattern 2: Sector momentum from news
        sector_sentiment = {}
        for news in news_data.get("news", []):
            sector = news.get("sector")
            if sector:
                if sector not in sector_sentiment:
                    sector_sentiment[sector] = {"positive": 0, "negative": 0}
                direction = news.get("impact_direction")
                if direction == "positive":
                    sector_sentiment[sector]["positive"] += 1
                elif direction == "negative":
                    sector_sentiment[sector]["negative"] += 1
        
        for sector, sentiment in sector_sentiment.items():
            if sentiment["positive"] >= 2:
                patterns.append({
                    "pattern": "sector_bullish_news",
                    "trigger": f"{sector} has {sentiment['positive']} positive news items",
                    "sectors_affected": [sector],
                    "confidence": 0.7,
                })
        
        return {
            "patterns": patterns,
            "count": len(patterns),
            "data_sources": {
                "commodities": len(commodity_data.get("commodities", {})),
                "events": events_data.get("count", 0),
                "news": news_data.get("count", 0),
            }
        }
        
    finally:
        db.close()


def get_affected_sectors(commodity: str) -> list[str]:
    """Get sectors affected by a commodity."""
    from src.db.database import SessionLocal
    from src.db.models import SectorExposure
    
    db = SessionLocal()
    sectors = []
    
    try:
        exposures = db.query(SectorExposure).filter(
            SectorExposure.commodity == commodity,
            SectorExposure.is_active == True,
        ).all()
        
        sectors = [e.sector for e in exposures]
        
    finally:
        db.close()
    
    return sectors