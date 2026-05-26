"""Celery tasks for monitoring geopolitical events."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import desc

from src.celery_app import app
from src.config import get_settings
from src.db.database import SessionLocal
from src.db.models import CommodityPrice, ETLRun, GeopoliticalEvent

logger = logging.getLogger(__name__)
settings = get_settings()


def _log_etl_run(db, pipeline_name: str):
    run = ETLRun(
        pipeline_name=pipeline_name,
        run_type="scheduled",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    return run


def _finish_etl_run(db, run, status="completed", records=0, error=None):
    run.status = status
    run.records_processed = records
    run.error_message = error
    run.completed_at = datetime.utcnow()
    run.duration_seconds = int((run.completed_at - run.started_at).total_seconds())
    db.commit()


@app.task(bind=True, name="etl.monitor_geopolitical_events")
def monitor_geopolitical_events(self):
    """Monitor geopolitical events and store significant ones.
    
    Runs every hour to detect new significant events.
    """
    logger.info("Starting geopolitical event monitoring")
    
    db = SessionLocal()
    run = _log_etl_run(db, "geopolitical_events_monitor")
    
    events_saved = 0
    errors = []
    
    try:
        from src.integrations.gdelt_client import GDELTFreeClient
        
        client = GDELTFreeClient()
        
        # Search for oil/conflict related news
        queries = [
            "oil price conflict Middle East",
            "Russia Ukraine war energy",
            "commodity supply disruption",
        ]
        
        all_articles = []
        for query in queries:
            articles = client.search_mentions(query, max_results=10)
            all_articles.extend(articles)
        
        # Store as basic events with pre-classified impacts
        from src.integrations.event_impact_classifier import get_event_classifier
        classifier = get_event_classifier()
        
        for article in all_articles:
            existing = db.query(GeopoliticalEvent).filter(
                GeopoliticalEvent.title == article.get("title")
            ).first()
            
            if not existing:
                event_dict = {
                    "title": article.get("title"),
                    "summary": article.get("summary", ""),
                    "country": article.get("country", "GLOBAL"),
                    "category": article.get("category", "news"),
                }
                # Pre-classify impact during ETL
                impact = classifier.classify(event_dict)
                
                raw = dict(article)
                if impact:
                    raw["impact"] = {
                        "commodity": impact.commodity,
                        "direction": impact.direction,
                        "magnitude": impact.magnitude,
                        "affected_sectors": impact.affected_sectors,
                    }
                
                event = GeopoliticalEvent(
                    title=article.get("title"),
                    summary=f"Source: {article.get('domain')}",
                    event_date=datetime.fromisoformat(
                        article.get("seendate", "").replace("Z", "+00:00")
                    ) if article.get("seendate") else datetime.utcnow(),
                    country="GLOBAL",
                    category="news",
                    source="gdelt_free",
                    raw_data=raw,
                )
                db.add(event)
                events_saved += 1
        
        logger.info(f"Saved {events_saved} events from free GDELT")
        
        db.commit()
        _finish_etl_run(db, run, records=events_saved)
        
    except Exception as e:
        logger.error(f"Event monitoring failed: {e}")
        errors.append(str(e))
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()
    
    return {"events_saved": events_saved, "errors": errors}


@app.task(bind=True, name="etl.generate_event_alerts")
def generate_event_alerts(self):
    """Generate commodity alerts based on recent events + price changes.
    
    Runs after event monitoring to generate actionable insights.
    """
    logger.info("Generating event-based commodity alerts")
    
    db = SessionLocal()
    
    try:
        # Get recent events with high confidence
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        recent_events = db.query(GeopoliticalEvent).filter(
            GeopoliticalEvent.event_date >= cutoff,
            GeopoliticalEvent.confidence >= 0.7,
        ).all()
        
        # Get current commodity prices with changes
        changes = get_commodity_changes_from_db(db, days=7)
        
        # Classify events
        from src.integrations.event_impact_classifier import get_event_classifier
        classifier = get_event_classifier()
        
        events_dict = [
            {
                "title": e.title,
                "summary": e.summary,
                "country": e.country,
                "category": e.category,
            }
            for e in recent_events
        ]
        
        alerts = classifier.get_commodity_alert(events_dict, changes)
        
        logger.info(f"Generated {len(alerts)} commodity alerts")
        
        return {"alerts": alerts, "count": len(alerts)}
        
    except Exception as e:
        logger.error(f"Alert generation failed: {e}")
        return {"alerts": [], "error": str(e)}
    finally:
        db.close()


def get_commodity_changes_from_db(db, days: int = 7) -> dict[str, float]:
    """Get commodity price changes from database (delegates to CausalService)."""
    from src.services.causal_service import CausalService
    service = CausalService(db)
    return {
        symbol: data.get("change_pct", 0)
        for symbol, data in service.get_commodity_changes(days=days).items()
    }


@app.task(bind=True, name="etl.get_significant_events")
def get_significant_events(self, hours: int = 24) -> list[dict[str, Any]]:
    """API-accessible task to get significant recent events.
    
    Returns:
        List of significant events with impact classification
    """
    db = SessionLocal()
    
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        events = (
            db.query(GeopoliticalEvent)
            .filter(GeopoliticalEvent.event_date >= cutoff)
            .order_by(desc(GeopoliticalEvent.confidence))
            .limit(20)
            .all()
        )
        
        # Get commodity changes
        changes = get_commodity_changes_from_db(db, days=7)
        
        # Classify impacts
        from src.integrations.event_impact_classifier import get_event_classifier
        classifier = get_event_classifier()
        
        results = []
        for event in events:
            event_dict = {
                "id": str(event.id),
                "title": event.title,
                "summary": event.summary,
                "country": event.country,
                "category": event.category,
                "event_date": event.event_date.isoformat() if event.event_date else None,
                "confidence": event.confidence,
                "goldstein_scale": event.goldstein_scale,
            }
            
            # Add impact classification
            impact = classifier.classify(event_dict)
            if impact:
                event_dict["impact"] = {
                    "commodity": impact.commodity,
                    "direction": impact.direction,
                    "magnitude": impact.magnitude,
                    "affected_sectors": impact.affected_sectors,
                    "confidence": impact.confidence,
                }
            
            results.append(event_dict)
        
        return results
        
    finally:
        db.close()