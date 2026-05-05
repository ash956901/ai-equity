"""News sync using free APIs (no API key required)."""

import logging
from datetime import datetime

from src.celery_app import app
from src.db.database import SessionLocal
from src.db.models import ClassifiedNews, ETLRun
from src.integrations.news_client import NewsAggregator
from src.integrations.news_classifier import get_news_classifier

logger = logging.getLogger(__name__)


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


@app.task(bind=True, name="etl.sync_news")
def sync_news(self):
    """Fetch and classify news using free APIs."""
    logger.info("Starting news sync with free APIs")
    
    db = SessionLocal()
    run = _log_etl_run(db, "news_sync")
    
    news_saved = 0
    
    try:
        aggregator = NewsAggregator()
        
        # Get general news
        all_news = aggregator.get_all_news(limit=30)
        logger.info(f"Fetched {len(all_news)} news items")
        
        # Classify
        classifier = get_news_classifier()
        classified = classifier.classify_batch(all_news)
        logger.info(f"Classified {len(classified)} news items")
        
        # Store
        for item in classified:
            existing = db.query(ClassifiedNews).filter(
                ClassifiedNews.url == item.get("url")
            ).first()
            
            if existing:
                continue
            
            news = ClassifiedNews(
                title=item.get("title", "")[:500],
                summary=item.get("summary", "")[:1000],
                url=item.get("url"),
                source=item.get("source"),
                published_at=datetime.fromisoformat(
                    item.get("published_at", "").replace("Z", "+00:00")
                ) if item.get("published_at") else datetime.utcnow(),
                topics=item.get("topics", []),
                importance_score=1.0,
                commodity=item.get("impact", {}).get("commodity"),
                sector=item.get("impact", {}).get("sector"),
                impact_type=item.get("impact", {}).get("impact_type"),
                impact_direction=item.get("impact", {}).get("direction"),
                classification_confidence=item.get("impact", {}).get("confidence"),
            )
            db.add(news)
            news_saved += 1
        
        db.commit()
        _finish_etl_run(db, run, records=news_saved)
        logger.info(f"Saved {news_saved} news items")
        
    except Exception as e:
        logger.error(f"News sync failed: {e}")
        _finish_etl_run(db, run, status="failed", error=str(e))
    finally:
        db.close()
    
    return {"news_saved": news_saved}


@app.task(bind=True, name="etl.get_market_sentiment")
def get_market_sentiment(self, hours: int = 24) -> dict:
    """Get market sentiment from recent classified news."""
    db = SessionLocal()
    
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        news = db.query(ClassifiedNews).filter(
            ClassifiedNews.published_at >= cutoff,
            ClassifiedNews.commodity.isnot(None),
        ).order_by(ClassifiedNews.published_at.desc()).limit(20).all()
        
        bullish = sum(1 for n in news if n.impact_direction == "positive")
        bearish = sum(1 for n in news if n.impact_direction == "negative")
        
        return {
            "bullish": bullish,
            "bearish": bearish,
            "total": len(news),
            "sentiment_score": (bullish - bearish) / max(len(news), 1),
        }
    finally:
        db.close()