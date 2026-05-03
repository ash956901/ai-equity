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
    worker_prefetch_multiplier=1,
    # Per-task concurrency caps via task routes / annotations:
    task_annotations={
        # LLM-heavy nightly jobs - cap to avoid runaway billing.
        "etl.tag_themes": {"rate_limit": "8/m"},
        "etl.extract_events": {"rate_limit": "8/m"},
        "etl.compute_daily_insights": {"rate_limit": "4/m"},
        "etl.revalidate_insights": {"rate_limit": "8/m"},
        # Network-heavy ingestion jobs.
        "etl.ingest_news": {"rate_limit": "12/m"},
        "etl.ingest_social": {"rate_limit": "12/m"},
        "etl.ingest_transcripts": {"rate_limit": "6/m"},
        "etl.ingest_macro_commodity": {"rate_limit": "12/m"},
    },
)

app.conf.beat_schedule = {
    # ------------------------------------------------------------------
    # Universe / financials maintenance (existing)
    # ------------------------------------------------------------------
    "sync-stock-universe-daily": {
        "task": "etl.sync_stock_universe",
        "schedule": crontab(hour=6, minute=0),
    },
    "enrich-companies-daily": {
        "task": "etl.enrich_companies",
        "schedule": crontab(hour=7, minute=0),
        "kwargs": {"batch_size": 200},
    },
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

    # ------------------------------------------------------------------
    # Filings + parsing (now actually persists)
    # ------------------------------------------------------------------
    "crawl-nse-filings-periodic": {
        "task": "etl.crawl_nse",
        "schedule": crontab(hour="9,11,13,15,17", minute=30),
    },
    "crawl-ir-pages-weekly": {
        "task": "etl.crawl_ir",
        "schedule": crontab(hour=2, minute=0, day_of_week="saturday"),
    },
    "parse-filings-backlog": {
        "task": "etl.parse_pending_filings",
        "schedule": crontab(minute="*/30"),
    },

    # ------------------------------------------------------------------
    # News
    # ------------------------------------------------------------------
    "news-ingest-portfolio-hourly": {
        "task": "etl.ingest_news",
        "schedule": crontab(minute=5),
        "kwargs": {"days": 1},
    },
    "news-ingest-universe-daily": {
        "task": "etl.ingest_news",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {"days": 2},
    },

    # ------------------------------------------------------------------
    # Transcripts
    # ------------------------------------------------------------------
    "ingest-transcripts-weekly": {
        "task": "etl.ingest_transcripts",
        "schedule": crontab(hour=3, minute=30, day_of_week="sunday"),
        "kwargs": {"limit": 50},
    },

    # ------------------------------------------------------------------
    # Social
    # ------------------------------------------------------------------
    "ingest-social-portfolio-15min": {
        "task": "etl.ingest_social",
        "schedule": crontab(minute="*/15"),
    },
    "reap-social-daily": {
        "task": "etl.reap_social",
        "schedule": crontab(hour=3, minute=15),
    },

    # ------------------------------------------------------------------
    # Macro + commodity
    # ------------------------------------------------------------------
    "ingest-macro-daily": {
        "task": "etl.ingest_macro_commodity",
        "schedule": crontab(hour=6, minute=30),
    },
    "ingest-commodity-energy-hourly": {
        "task": "etl.ingest_macro_commodity",
        "schedule": crontab(minute=20),
    },

    # ------------------------------------------------------------------
    # Insight engine (offline agents)
    # ------------------------------------------------------------------
    "tag-themes-nightly": {
        "task": "etl.tag_themes",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {"limit": 200},
    },
    "extract-events-nightly": {
        "task": "etl.extract_events",
        "schedule": crontab(hour=2, minute=30),
    },
    "compute-daily-insights": {
        "task": "etl.compute_daily_insights",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"max_insights": 25},
    },
    "revalidate-insights": {
        "task": "etl.revalidate_insights",
        "schedule": crontab(hour=4, minute=30),
    },

    # ------------------------------------------------------------------
    # Phase 2: Knowledge graph
    # ------------------------------------------------------------------
    "graph-backfill-weekly": {
        "task": "etl.backfill_graph_edges",
        "schedule": crontab(hour=1, minute=15, day_of_week="monday"),
    },
    "mine-supply-chain-weekly": {
        "task": "etl.mine_supply_chain",
        "schedule": crontab(hour=1, minute=45, day_of_week="tuesday"),
    },
    "mine-patterns-nightly": {
        "task": "etl.mine_patterns",
        "schedule": crontab(hour=3, minute=20),
    },

    # ------------------------------------------------------------------
    # Round 2: filing summarisation, alerts, ETL hygiene
    # ------------------------------------------------------------------
    "summarize-pending-filings-hourly": {
        "task": "etl.summarize_pending_filings",
        "schedule": crontab(minute=10),
        "kwargs": {"batch_size": 50},
    },
    "evaluate-alert-rules-5min": {
        "task": "etl.evaluate_alert_rules",
        "schedule": crontab(minute="*/5"),
        "kwargs": {"batch_size": 200},
    },
    "deliver-alert-events-5min": {
        "task": "etl.deliver_alert_events",
        "schedule": crontab(minute="*/5"),
        "kwargs": {"batch_size": 100},
    },
    "monitor-stuck-runs-hourly": {
        "task": "etl.monitor_stuck_runs",
        "schedule": crontab(minute=45),
        "kwargs": {"max_age_minutes": 120},
    },
    "discover-new-listings-daily": {
        "task": "etl.discover_new_listings",
        "schedule": crontab(hour=6, minute=15),
        "kwargs": {"lookback_hours": 24, "limit": 50},
    },
}
