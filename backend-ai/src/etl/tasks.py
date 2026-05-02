"""Celery tasks for ETL pipelines."""

import logging
from datetime import datetime
from typing import Any, Optional
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
    context = None
    try:
        from src.services.market_data.context import MarketDataContext
        from src.services.market_data.enrichment_service import CompanyEnrichmentService

        companies = (
            db.query(Company)
            .filter(
                Company.listing_status == "active",
                (Company.sector.is_(None)) | (Company.industry.is_(None)),
            )
            .limit(batch_size)
            .all()
        )

        context = MarketDataContext(db)
        enrichment_service = CompanyEnrichmentService(context)
        enriched = 0
        for company in companies:
            try:
                result = enrichment_service.enrich_company(company.id)
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
        if context is not None:
            context.close()
        db.close()


@app.task(bind=True, name="etl.enrich_single_company")
def enrich_single_company(self, company_id: str):
    """On-demand enrichment for a specific company."""
    db = SessionLocal()
    context = None
    try:
        from src.services.market_data.context import MarketDataContext
        from src.services.market_data.enrichment_service import CompanyEnrichmentService

        context = MarketDataContext(db)
        service = CompanyEnrichmentService(context)
        return service.enrich_company(UUID(company_id))
    except Exception as e:
        logger.exception("Single company enrich failed for %s", company_id)
        raise
    finally:
        if context is not None:
            context.close()
        db.close()


# ------------------------------------------------------------------ #
#  Financial data refresh                                              #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.refresh_financials_batch")
def refresh_financials_batch(self, batch_size: int = 100):
    """Scrape and persist financial data for companies lacking it."""
    db = SessionLocal()
    run = _log_etl_run(db, "financials_refresh")
    context = None
    try:
        from src.services.market_data.context import MarketDataContext
        from src.services.market_data.financials_service import FinancialStatementsService

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

        context = MarketDataContext(db)
        financials_service = FinancialStatementsService(context)

        fetched = 0
        for company in companies:
            try:
                result = financials_service.get_financials(company.id)
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
        if context is not None:
            context.close()
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
    from src.etl.ingestion_service import DocumentIngestionService
    
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
        
        # Integrate with ingestion service to download filings
        ingestion_service = DocumentIngestionService(db)
        company = db.query(Company).filter(Company.id == cid).first() if cid else None
        
        # If we have a specific company, use its ID; otherwise, we'll need to map symbols to companies
        if company:
            downloaded = 0
            for result in results:
                filing = ingestion_service.ingest_filing(company.id, result)
                if filing:
                    downloaded += 1
                    process_filing.delay(str(filing.id))
            _finish_etl_run(db, run, records=downloaded)
        else:
            # For batch processing, we need to find companies by symbol
            downloaded = 0
            for result in results:
                symbol = result.get("symbol")
                if symbol:
                    # Try to find company by NSE symbol
                    company = db.query(Company).filter(
                        (Company.ticker_nse == symbol) | (Company.tl_nse == symbol)
                    ).first()
                    if company is None:
                        # Try to find by BSE symbol
                        company = db.query(Company).filter(
                            (Company.ticker_nse == symbol) | (Company.ticker_bse == symbol)
                        ).first()
                    
                    if company:
                        filing = ingestion_service.ingest_filing(company.id, result)
                        if filing:
                            downloaded += 1
                            process_filing.delay(str(filing.id))
            _finish_etl_run(db, run, records=downloaded)
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
    finally:
        db.close()


@app.task(bind=True, name="etl.crawl_bse")
def crawl_bse_filings(
    self,
    company_id: Optional[str] = None,
    since_date: Optional[str] = None,
):
    """Crawl BSE filings for companies."""
    from src.etl.ingestion_service import DocumentIngestionService
    from src.etl.crawler_bse import BSECrawler
    
    db = SessionLocal()
    run = _log_etl_run(
        db,
        "bse_filings",
        company_id=UUID(company_id) if company_id else None,
    )
    try:
        crawler = BSECrawler()
        cid = UUID(company_id) if company_id else None
        results = crawler.crawl(company_id=cid, since_date=since_date)
        
        # Integrate with ingestion service to download filings
        ingestion_service = DocumentIngestionService(db)
        company = db.query(Company).filter(Company.id == cid).first() if cid else None
        
        # If we have a specific company, use its ID; otherwise, we'll need to map symbols to companies
        if company:
            downloaded = 0
            for result in results:
                filing = ingestion_service.ingest_filing(company.id, result)
                if filing:
                    downloaded += 1
                    process_filing.delay(str(filing.id))
            _finish_etl_run(db, run, records=downloaded)
        else:
            # For batch processing, we need to find companies by symbol
            downloaded = 0
            for result in results:
                symbol = result.get("symbol")
                if symbol:
                    # Try to find company by BSE symbol
                    company = db.query(Company).filter(
                        (Company.ticker_bse == symbol) | (Company.ticker_nse == symbol)
                    ).first()
                    if company is None:
                        # Try to find by NSE symbol as fallback
                        company = db.query(Company).filter(
                            Company.ticker_nse == symbol
                        ).first()
                    
                    if company:
                        filing = ingestion_service.ingest_filing(company.id, result)
                        if filing:
                            downloaded += 1
                            process_filing.delay(str(filing.id))
            _finish_etl_run(db, run, records=downloaded)
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
    import importlib

    celery_mod = importlib.import_module("celery")
    chain_fn = getattr(celery_mod, "chain")

    enrich_sig: Any = enrich_single_company.s(company_id)
    nse_sig: Any = crawl_nse_filings.s(company_id=company_id)
    ir_sig: Any = crawl_ir_pages.s(company_id=company_id)
    workflow: Any = chain_fn(enrich_sig, nse_sig, ir_sig)
    workflow.apply_async()


# ------------------------------------------------------------------ #
#  Document Processing pipeline                                        #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.process_filing")
def process_filing(self, filing_id: str):
    """Process a downloaded filing through the semantic processing pipeline."""
    db = SessionLocal()
    run = _log_etl_run(db, "process_filing")
    try:
        from src.db.models import Filing, Company
        from src.etl.transform_task import ETLTransformTask
        from src.etl.load_task import ETLLoadTask
        
        filing = db.query(Filing).filter(Filing.id == UUID(filing_id)).first()
        if not filing or not filing.raw_uri:
            logger.warning("Filing not found or has no raw_uri: %s", filing_id)
            return
            
        file_path = filing.raw_uri
        
        # Get metadata
        metadata = {
            "company_id": str(filing.company_id),
            "filing_id": str(filing.id),
            "filing_type": filing.filing_type or "",
            "filing_date": filing.filing_date.isoformat() if filing.filing_date else "",
            "document_type": filing.filing_type or "",
        }
        
        # Transform
        transformer = ETLTransformTask()
        chunks = transformer.process_filing(
            file_path=file_path,
            **metadata
        )
        
        # Load
        loader = ETLLoadTask()
        loaded_count = loader.load_chunks(chunks)
        
        # Update filing status
        filing.status = "processed"
        db.commit()
        
        _finish_etl_run(db, run, records=loaded_count)
        return {"loaded": loaded_count}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("Filing processing failed")
        raise
    finally:
        db.close()
