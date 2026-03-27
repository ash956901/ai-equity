"""Celery application for background workers."""

from celery import Celery
from celery.schedules import crontab

from src.config import get_settings

settings = get_settings()

app = Celery(
    "equity_research",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend or settings.redis_url or settings.celery_broker_url,
    include=[
        "src.etl.tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_prefetch_multiplier=4,
)

app.conf.beat_schedule = {
    # Sync the full NSE+BSE stock universe daily at 6:00 AM IST (before market open)
    "sync-stock-universe-daily": {
        "task": "etl.sync_stock_universe",
        "schedule": crontab(hour=6, minute=0),
    },
    # Enrich companies missing sector/industry data — daily at 7:00 AM IST
    "enrich-companies-daily": {
        "task": "etl.enrich_companies",
        "schedule": crontab(hour=7, minute=0),
        "kwargs": {"batch_size": 200},
    },
    # Refresh financial data for companies that lack it — twice daily
    "refresh-financials-morning": {
        "task": "etl.refresh_financials_batch",
        "schedule": crontab(hour=8, minute=0),
        "kwargs": {"batch_size": 100},
    },
    "refresh-financials-evening": {
        "task": "etl.refresh_financials_batch",
        "schedule": crontab(hour=18, minute=0),
        "kwargs": {"batch_size": 100},
    },
    # Crawl NSE filings every 2 hours during market hours (9 AM - 6 PM IST)
    "crawl-nse-filings-periodic": {
        "task": "etl.crawl_nse",
        "schedule": crontab(hour="9,11,13,15,17", minute=30),
    },
    # Crawl IR pages weekly on Saturday at 2 AM IST
    "crawl-ir-pages-weekly": {
        "task": "etl.crawl_ir",
        "schedule": crontab(hour=2, minute=0, day_of_week="saturday"),
    },
}
