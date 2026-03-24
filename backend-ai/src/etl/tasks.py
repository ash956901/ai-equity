"""Celery tasks for ETL pipelines."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.celery_app import app
from src.db.database import SessionLocal
from src.db.models import Company, ETLRun
from src.etl.crawler_nse import NSECrawler
from src.etl.crawler_ir import IRCrawler

logger = logging.getLogger(__name__)


def _log_etl_run(db, pipeline_name: str, run_type: str = "scheduled", company_id=None):
    run = ETLRun(
        pipeline_name=pipeline_name,
        run_type=run_type,
        company_id=company_id,
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


# ------------------------------------------------------------------ #
#  Stock universe sync                                                 #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.sync_stock_universe")
def sync_stock_universe(self):
    """Download ALL NSE + BSE listed companies into the database.

    Sources: Upstox instrument master CSV → NSE/BSE website APIs.
    Runs daily at 6:00 AM IST before market open.
    """
    db = SessionLocal()
    run = _log_etl_run(db, "stock_universe_sync")
    try:
        from src.services.stock_universe import StockUniverseService

        svc = StockUniverseService(db)
        stats = svc.sync_full_universe()
        _finish_etl_run(db, run, records=stats.get("created", 0) + stats.get("updated", 0))
        logger.info("Universe sync: %s", stats)
        return stats
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("Universe sync failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Company data enrichment                                             #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.enrich_companies")
def enrich_companies_batch(self, batch_size: int = 200):
    """Enrich company profiles (sector, industry, market cap) from web sources.

    Targets companies missing sector/industry data.
    """
    db = SessionLocal()
    run = _log_etl_run(db, "company_enrichment")
    try:
        from src.services.realtime_data import RealTimeDataService

        companies = (
            db.query(Company)
            .filter(
                Company.listing_status == "active",
                (Company.sector.is_(None)) | (Company.industry.is_(None)),
            )
            .limit(batch_size)
            .all()
        )
        enriched = 0
        for company in companies:
            try:
                svc = RealTimeDataService(db)
                result = svc.enrich_company(company.id)
                if result.get("enriched"):
                    enriched += 1
            except Exception as e:
                logger.debug("Enrich failed for %s: %s", company.name, e)

        _finish_etl_run(db, run, records=enriched)
        return {"enriched": enriched, "attempted": len(companies)}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.enrich_single_company")
def enrich_single_company(self, company_id: str):
    """On-demand enrichment for a specific company."""
    db = SessionLocal()
    try:
        from src.services.realtime_data import RealTimeDataService

        svc = RealTimeDataService(db)
        return svc.enrich_company(UUID(company_id))
    except Exception as e:
        logger.exception("Single company enrich failed for %s", company_id)
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Financial data refresh                                              #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.refresh_financials_batch")
def refresh_financials_batch(self, batch_size: int = 100):
    """Scrape and persist financial data for companies lacking it."""
    db = SessionLocal()
    run = _log_etl_run(db, "financials_refresh")
    try:
        from src.services.realtime_data import RealTimeDataService

        from sqlalchemy import func
        from src.db.models import FinancialStatementRaw

        companies_with_data = (
            db.query(FinancialStatementRaw.company_id)
            .distinct()
            .subquery()
        )
        companies = (
            db.query(Company)
            .filter(
                Company.listing_status == "active",
                ~Company.id.in_(db.query(companies_with_data.c.company_id)),
            )
            .limit(batch_size)
            .all()
        )

        fetched = 0
        for company in companies:
            try:
                svc = RealTimeDataService(db)
                result = svc.get_financials(company.id)
                if result.get("periods") or result.get("raw_data"):
                    fetched += 1
            except Exception as e:
                logger.debug("Financials fetch failed for %s: %s", company.name, e)

        _finish_etl_run(db, run, records=fetched)
        return {"fetched": fetched, "attempted": len(companies)}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Existing NSE / IR crawlers                                          #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_nse")
def crawl_nse_filings(
    self,
    company_id: Optional[str] = None,
    since_date: Optional[str] = None,
):
    """Crawl NSE filings for companies."""
    db = SessionLocal()
    run = _log_etl_run(
        db,
        "nse_filings",
        company_id=UUID(company_id) if company_id else None,
    )
    try:
        crawler = NSECrawler()
        cid = UUID(company_id) if company_id else None
        results = crawler.crawl(company_id=cid, since_date=since_date)
        _finish_etl_run(db, run, records=len(results))
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
    finally:
        db.close()


@app.task(bind=True, name="etl.crawl_ir")
def crawl_ir_pages(
    self,
    company_id: Optional[str] = None,
):
    """Crawl investor relations pages."""
    db = SessionLocal()
    run = _log_etl_run(
        db,
        "ir_crawler",
        company_id=UUID(company_id) if company_id else None,
    )
    try:
        crawler = IRCrawler()
        cid = UUID(company_id) if company_id else None
        results = crawler.crawl(company_id=cid)
        _finish_etl_run(db, run, records=len(results))
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Full company refresh (on-demand)                                    #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.refresh_company")
def refresh_company(self, company_id: str):
    """Full refresh for a single company: enrich + financials + filings."""
    from celery import chain

    chain(
        enrich_single_company.s(company_id),
        crawl_nse_filings.s(company_id=company_id),
        crawl_ir_pages.s(company_id=company_id),
    ).apply_async()
