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
from src.etl.crawler_bse import BSECrawler
from src.etl.crawler_sebi import SEBICrawler
from src.etl.crawler_screener import ScreenerCrawler
from src.etl.crawler_amfi import AMFICrawler
from src.etl.crawler_mfapi import MFApiCrawler
from src.etl.crawler_datagov import DataGovCrawler
from src.etl.crawler_rbi import RBICrawler
from src.etl.crawler_nse_bhavcopy import NSEBhavcopycrawler
from src.etl.crawler_news_rss import NewsRSSCrawler

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
        
        # Integrate with ingestion service to download filings
        ingestion_service = DocumentIngestionService(db)
        company = db.query(Company).filter(Company.id == cid).first() if cid else None
        
        symbol = company.ticker_nse if company else None
        results = crawler.crawl(company_id=cid, symbol=symbol, since_date=since_date)
        
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
        
        # Integrate with ingestion service to download filings
        ingestion_service = DocumentIngestionService(db)
        company = db.query(Company).filter(Company.id == cid).first() if cid else None
        
        symbol = company.ticker_bse if company else None
        results = crawler.crawl(company_id=cid, symbol=symbol, since_date=since_date)
        
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
        result = transformer.process_filing(
            file_path=file_path,
            **metadata
        )
        
        chunks = result.get("chunks", [])
        enrichment = result.get("enrichment", {})
        
        # Load chunks to Qdrant
        loader = ETLLoadTask()
        loaded_count = loader.load_chunks(chunks)
        
        # Update filing status and save enrichment metadata to DB
        filing.status = "processed"
        
        if filing.metadata_ is None:
            filing.metadata_ = {}
            
        # Ensure we don't overwrite existing metadata completely
        current_meta = dict(filing.metadata_)
        current_meta['timeline_summary'] = enrichment.get("timeline_summary", "")
        current_meta['red_flags'] = enrichment.get("red_flags", [])
        current_meta['extracted_metrics'] = enrichment.get("metrics", {})
        filing.metadata_ = current_meta
        
        db.commit()
        
        _finish_etl_run(db, run, records=loaded_count)
        return {"loaded": loaded_count}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("Filing processing failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  SEBI / NSE+BSE filings (via SEBICrawler)                           #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_sebi")
def crawl_sebi_filings(
    self,
    symbol: Optional[str] = None,
    bse_code: Optional[str] = None,
    since_date: Optional[str] = None,
):
    """Crawl SEBI-curated filings from NSE+BSE endpoints.

    Uses SEBICrawler which hits the actual NSE/BSE JSON APIs that
    SEBI's curation page links to.
    """
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "sebi_filings")
    try:
        crawler = SEBICrawler()
        results = crawler.crawl(
            symbol=symbol,
            bse_code=bse_code,
            since_date=since_date,
        )

        ingestion = DocumentIngestionService(db)
        downloaded = 0
        for result in results:
            sym = result.get("symbol", symbol)
            if not sym:
                continue

            company = db.query(Company).filter(
                (Company.ticker_nse == sym) | (Company.ticker_bse == sym)
            ).first()

            if company:
                filing = ingestion.ingest_filing(company.id, result)
                if filing:
                    downloaded += 1
                    process_filing.delay(str(filing.id))

        _finish_etl_run(db, run, records=downloaded)
        return {"source": "SEBI", "fetched": len(results), "ingested": downloaded}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("SEBI crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Screener.in financial snapshots                                     #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_screener")
def crawl_screener(
    self,
    symbol: Optional[str] = None,
    symbols: Optional[list] = None,
    consolidated: bool = True,
):
    """Crawl screener.in for 10-year financials, ratios, documents.

    If symbol is given, crawls just that company.
    If symbols list is given, crawls all.
    If neither, crawls active companies in the DB that lack screener data.
    """
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "screener_financials")
    try:
        crawler = ScreenerCrawler()
        ingestion = DocumentIngestionService(db)
        total = 0

        target_symbols = []
        if symbol:
            target_symbols = [symbol]
        elif symbols:
            target_symbols = symbols
        else:
            # Crawl first 10 active companies that don't have screener data yet
            companies = (
                db.query(Company)
                .filter(Company.listing_status == "active", Company.ticker_nse.isnot(None))
                .limit(10)
                .all()
            )
            target_symbols = [c.ticker_nse for c in companies if c.ticker_nse]

        for sym in target_symbols:
            data = crawler.crawl(sym, consolidated=consolidated)
            if not data.get("profit_loss", {}).get("data"):
                logger.warning("Empty screener data for %s", sym)
                continue

            company = db.query(Company).filter(
                (Company.ticker_nse == sym.upper()) | (Company.ticker_bse == sym.upper())
            ).first()

            if company:
                total += ingestion.ingest_screener_data(company.id, data)

                # Also ingest document links (annual reports, concalls)
                for doc_type in ["annual_reports", "concalls", "credit_ratings"]:
                    for doc in data.get("documents", {}).get(doc_type, []):
                        link = doc.get("link") or doc.get("transcript") or doc.get("ppt")
                        if link:
                            ingestion.ingest_filing(company.id, {
                                "attachment_url": link,
                                "subject": f"{doc_type}: {doc.get('year', doc.get('month', ''))}",
                                "filing_type": doc_type,
                                "source": "screener.in",
                            })

        _finish_etl_run(db, run, records=total)
        return {"source": "screener.in", "symbols": len(target_symbols), "ingested": total}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("Screener crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  AMFI NAV                                                            #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_amfi")
def crawl_amfi_nav(self, fund_house: Optional[str] = None):
    """Fetch daily mutual fund NAVs from AMFI (~14,000+ schemes)."""
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "amfi_nav")
    try:
        crawler = AMFICrawler()
        data = crawler.crawl(fund_house=fund_house)

        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("amfi_nav", data)

        _finish_etl_run(db, run, records=count)
        return {"source": "AMFI", "schemes": count}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("AMFI crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  mfapi.in                                                            #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_mfapi")
def crawl_mfapi(self, scheme_codes: Optional[list] = None, limit: int = 10):
    """Fetch MF NAV history from mfapi.in."""
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "mfapi")
    try:
        crawler = MFApiCrawler()
        data = crawler.crawl(scheme_codes=scheme_codes, limit=limit)

        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("mfapi", data)

        _finish_etl_run(db, run, records=count)
        return {"source": "mfapi.in", "schemes": count}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("mfapi crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  data.gov.in MCA                                                     #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_datagov")
def crawl_datagov(self, search: str = "company master", limit: int = 20):
    """Discover MCA datasets on data.gov.in."""
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "datagov_mca")
    try:
        crawler = DataGovCrawler()
        data = crawler.discover_datasets(search=search, limit=limit)

        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("datagov_mca", data)

        _finish_etl_run(db, run, records=count)
        return {"source": "data.gov.in", "datasets": count}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("data.gov.in crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  RBI macro data                                                      #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_rbi")
def crawl_rbi_macro(self):
    """Fetch RBI macro indicators (policy rates, M3, reserves, etc.)."""
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "rbi_macro")
    try:
        crawler = RBICrawler()
        data = crawler.crawl()

        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("rbi_macro", data)

        _finish_etl_run(db, run, records=count)
        return {
            "source": "RBI",
            "indicators": len(data.get("policy_rates", {})),
            "table_rows": len(data.get("key_rates_table", [])),
        }
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("RBI crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  NSE Bhavcopy (daily OHLCV)                                         #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_bhavcopy")
def crawl_nse_bhavcopy(self, symbol: Optional[str] = None):
    """Fetch daily NSE bhavcopy (OHLCV + delivery data)."""
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "nse_bhavcopy")
    try:
        crawler = NSEBhavcopycrawler()
        data = crawler.crawl(symbol=symbol)

        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("nse_bhavcopy", data)

        _finish_etl_run(db, run, records=count)
        return {
            "source": "NSE_Bhavcopy",
            "records": count,
            "date": data[0].get("date") if data else "N/A",
        }
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("NSE Bhavcopy crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  News RSS (ET Markets + LiveMint)                                    #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_news_rss")
def crawl_news_rss(self, feeds: Optional[list] = None):
    """Fetch financial news from ET Markets + LiveMint RSS feeds.

    Articles are persisted to the news_articles DB table with dedup.
    """
    from src.etl.ingestion_service import DocumentIngestionService

    db = SessionLocal()
    run = _log_etl_run(db, "news_rss")
    try:
        crawler = NewsRSSCrawler()
        articles = crawler.crawl(feeds=feeds)

        ingestion = DocumentIngestionService(db)
        created = ingestion.ingest_news_articles(articles)

        _finish_etl_run(db, run, records=created)
        return {"source": "RSS", "fetched": len(articles), "new": created}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        logger.exception("News RSS crawl failed")
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Full company refresh (updated with all sources)                     #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.refresh_company")
def refresh_company(self, company_id: str):
    """Full refresh for a single company: enrich + financials + all filing sources."""
    import importlib

    celery_mod = importlib.import_module("celery")
    chain_fn = getattr(celery_mod, "chain")

    enrich_sig: Any = enrich_single_company.s(company_id)
    nse_sig: Any = crawl_nse_filings.s(company_id=company_id)
    bse_sig: Any = crawl_bse_filings.s(company_id=company_id)
    ir_sig: Any = crawl_ir_pages.s(company_id=company_id)
    workflow: Any = chain_fn(enrich_sig, nse_sig, bse_sig, ir_sig)
    workflow.apply_async()


# ------------------------------------------------------------------ #
#  Full pipeline orchestrator                                          #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.run_full_pipeline")
def run_full_pipeline(self):
    """Run the complete ETL pipeline — all crawlers in sequence.

    Intended for daily scheduled execution (e.g., 7 PM IST after market close).

    Pipeline order:
      1. NSE Bhavcopy (daily OHLCV)
      2. AMFI NAV (daily MF NAVs)
      3. News RSS (ET + Mint articles)
      4. NSE + BSE filings
      5. SEBI filings
      6. RBI macro indicators
      7. data.gov.in MCA datasets
    """
    results = {}

    try:
        results["bhavcopy"] = crawl_nse_bhavcopy()
    except Exception as e:
        results["bhavcopy"] = {"error": str(e)}

    try:
        results["amfi"] = crawl_amfi_nav()
    except Exception as e:
        results["amfi"] = {"error": str(e)}

    try:
        results["news_rss"] = crawl_news_rss()
    except Exception as e:
        results["news_rss"] = {"error": str(e)}

    try:
        results["nse"] = crawl_nse_filings()
    except Exception as e:
        results["nse"] = {"error": str(e)}

    try:
        results["bse"] = crawl_bse_filings()
    except Exception as e:
        results["bse"] = {"error": str(e)}

    try:
        results["sebi"] = crawl_sebi_filings()
    except Exception as e:
        results["sebi"] = {"error": str(e)}

    try:
        results["rbi"] = crawl_rbi_macro()
    except Exception as e:
        results["rbi"] = {"error": str(e)}

    try:
        results["datagov"] = crawl_datagov()
    except Exception as e:
        results["datagov"] = {"error": str(e)}

    logger.info("Full pipeline complete: %s", results)
    return results
