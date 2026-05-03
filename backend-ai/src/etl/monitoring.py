"""ETL hygiene tasks: stuck-run monitor and self-discovery for new listings."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_

from src.db.database import SessionLocal
from src.db.models import AlertEvent, Company, ETLRun

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
#  Stuck-run monitor                                                     #
# --------------------------------------------------------------------- #


def reap_stuck_runs(*, max_age_minutes: int = 120) -> dict[str, Any]:
    """Mark `etl_runs.status='running'` rows older than ``max_age_minutes`` as
    failed. Each one writes an alert_event row tagged ``etl_stuck`` so the
    delivery pipeline can surface it without bespoke wiring.

    Returns counts of {considered, reaped}.
    """
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    reaped = 0
    considered = 0
    try:
        rows = (
            db.query(ETLRun)
            .filter(ETLRun.status == "running")
            .filter(ETLRun.started_at < cutoff)
            .order_by(ETLRun.started_at.asc())
            .limit(200)
            .all()
        )
        considered = len(rows)
        for run in rows:
            run.status = "failed"
            run.error_message = (run.error_message or "") + " [stuck reap]"
            run.completed_at = datetime.utcnow()
            run.duration_seconds = int(
                (run.completed_at - run.started_at).total_seconds()
            )
            reaped += 1
            try:
                from src.observability import record_etl_run

                record_etl_run(run.pipeline_name, "stuck_reap")
            except Exception:
                pass
        db.commit()
        return {"considered": considered, "reaped": reaped}
    finally:
        db.close()


# --------------------------------------------------------------------- #
#  Self-discovery for new NSE/BSE listings                              #
# --------------------------------------------------------------------- #


def discover_new_listings(*, lookback_hours: int = 24, limit: int = 25) -> dict[str, Any]:
    """Find Company rows created within the last ``lookback_hours`` and
    chain them through the ingest pipeline (enrich → NSE crawl → IR crawl)
    so a freshly listed company has data within minutes.

    Returns {discovered, scheduled}.
    """
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
    db = SessionLocal()
    try:
        rows = (
            db.query(Company)
            .filter(Company.created_at >= cutoff)
            .filter(Company.listing_status == "active")
            .order_by(Company.created_at.desc())
            .limit(limit)
            .all()
        )
        discovered = len(rows)
        scheduled = 0
        for c in rows:
            try:
                from src.etl.tasks import refresh_company

                refresh_company.delay(str(c.id))
                scheduled += 1
            except Exception as exc:
                logger.debug("could not schedule refresh for %s: %s", c.id, exc)
        return {"discovered": discovered, "scheduled": scheduled}
    finally:
        db.close()
