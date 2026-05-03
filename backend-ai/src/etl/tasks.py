"""Celery tasks for ETL pipelines."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from src.celery_app import app
from src.db.database import SessionLocal
from src.db.models import Company, ETLRun, Filing
from src.etl.crawler_ir import IRCrawler
from src.etl.crawler_nse import NSECrawler

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


def _finish_etl_run(db, run, status="completed", records=0, error=None, metadata=None):
    run.status = status
    run.records_processed = records
    run.error_message = error
    run.completed_at = datetime.utcnow()
    run.duration_seconds = int((run.completed_at - run.started_at).total_seconds())
    if metadata is not None:
        run.metadata_ = metadata
    db.commit()
    try:
        from src.observability import record_etl_run

        record_etl_run(run.pipeline_name, status)
    except Exception:
        pass


# ------------------------------------------------------------------ #
#  Stock universe sync                                               #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.sync_stock_universe")
def sync_stock_universe(self):
    """Download ALL NSE + BSE listed companies into the database."""
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
#  Company data enrichment                                           #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.enrich_companies")
def enrich_companies_batch(self, batch_size: int = 200):
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
    db = SessionLocal()
    context = None
    try:
        from src.services.market_data.context import MarketDataContext
        from src.services.market_data.enrichment_service import CompanyEnrichmentService

        context = MarketDataContext(db)
        service = CompanyEnrichmentService(context)
        return service.enrich_company(UUID(company_id))
    except Exception:
        logger.exception("Single company enrich failed for %s", company_id)
        raise
    finally:
        if context is not None:
            context.close()
        db.close()


# ------------------------------------------------------------------ #
#  Financial data refresh                                            #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.refresh_financials_batch")
def refresh_financials_batch(self, batch_size: int = 100):
    db = SessionLocal()
    run = _log_etl_run(db, "financials_refresh")
    context = None
    try:
        from src.services.market_data.context import MarketDataContext
        from src.services.market_data.financials_service import FinancialStatementsService

        from src.db.models import FinancialStatementRaw

        companies_with_data = (
            db.query(FinancialStatementRaw.company_id).distinct().subquery()
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
#  Filing crawl + parse pipeline                                     #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.crawl_nse")
def crawl_nse_filings(
    self,
    company_id: Optional[str] = None,
    since_date: Optional[str] = None,
):
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
        for r in results:
            try:
                parse_filing.delay(r["filing_id"])
            except Exception:
                pass
        _finish_etl_run(db, run, records=len(results), metadata={"new_filings": len(results)})
        return {"new_filings": len(results)}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.crawl_ir")
def crawl_ir_pages(
    self,
    company_id: Optional[str] = None,
):
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
        for r in results:
            try:
                parse_filing.delay(r["filing_id"])
            except Exception:
                pass
        _finish_etl_run(db, run, records=len(results), metadata={"new_filings": len(results)})
        return {"new_filings": len(results)}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.parse_filing")
def parse_filing(self, filing_id: str):
    """Parse a single filing into pages + Qdrant chunks, then schedule
    the AI one-liner summary for the Timeline."""
    from src.etl.doc_parser import parse_and_index_filing

    db = SessionLocal()
    run = _log_etl_run(
        db, "filing_parser", company_id=None, run_type="chained"
    )
    try:
        result = parse_and_index_filing(UUID(filing_id))
        _finish_etl_run(
            db,
            run,
            records=result.get("chunks", 0),
            metadata={"filing_id": filing_id, **result},
        )
        # Fire-and-forget summary generation (idempotent on filing_id).
        try:
            summarize_filing_task.delay(filing_id)
        except Exception:
            logger.debug("Could not enqueue summarize_filing for %s", filing_id)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Filing one-liner summaries (Timeline feed)                        #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.summarize_filing")
def summarize_filing_task(self, filing_id: str):
    """Generate and persist an AI one-liner for a single filing."""
    from src.etl.filing_summary import summarize_filing

    db = SessionLocal()
    run = _log_etl_run(
        db, "filing_summary", company_id=None, run_type="chained"
    )
    try:
        result = summarize_filing(UUID(filing_id))
        _finish_etl_run(
            db, run, records=1 if result.get("status") == "ok" else 0, metadata=result
        )
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.summarize_pending_filings")
def summarize_pending_filings_task(self, batch_size: int = 50):
    """Drain filings without a FilingSummary row."""
    from src.etl.filing_summary import summarize_pending_filings

    db = SessionLocal()
    run = _log_etl_run(db, "filing_summary_backlog")
    try:
        result = summarize_pending_filings(batch_size=batch_size)
        _finish_etl_run(db, run, records=result.get("summarised", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Alert evaluation + delivery                                       #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.evaluate_alert_rules")
def evaluate_alert_rules_task(self, batch_size: int = 200):
    """Evaluate all active alert rules; persist firings to alert_events."""
    from src.etl.alert_evaluator import evaluate_active_rules

    db = SessionLocal()
    run = _log_etl_run(db, "alert_evaluator")
    try:
        result = evaluate_active_rules(batch_size=batch_size)
        _finish_etl_run(db, run, records=result.get("fired", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.deliver_alert_events")
def deliver_alert_events_task(self, batch_size: int = 100):
    """Promote pending alert_events to in_app status (email/FCM follow-up)."""
    from src.etl.alert_evaluator import deliver_pending_events

    db = SessionLocal()
    run = _log_etl_run(db, "alert_delivery")
    try:
        result = deliver_pending_events(batch_size=batch_size)
        _finish_etl_run(db, run, records=result.get("delivered", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Hygiene: stuck-run reaper + new-listing self-discovery            #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.monitor_stuck_runs")
def monitor_stuck_runs_task(self, max_age_minutes: int = 120):
    """Mark long-running ETL rows as failed so the queue doesn't silently stall."""
    from src.etl.monitoring import reap_stuck_runs

    db = SessionLocal()
    run = _log_etl_run(db, "stuck_reaper")
    try:
        result = reap_stuck_runs(max_age_minutes=max_age_minutes)
        _finish_etl_run(db, run, records=result.get("reaped", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.discover_new_listings")
def discover_new_listings_task(self, lookback_hours: int = 24, limit: int = 25):
    """Schedule full ingest for any company added in the lookback window."""
    from src.etl.monitoring import discover_new_listings

    db = SessionLocal()
    run = _log_etl_run(db, "new_listing_discovery")
    try:
        result = discover_new_listings(lookback_hours=lookback_hours, limit=limit)
        _finish_etl_run(db, run, records=result.get("scheduled", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.parse_pending_filings")
def parse_pending_filings(self, batch_size: int = 25):
    """Drain Filing rows whose status is still 'pending'."""
    db = SessionLocal()
    run = _log_etl_run(db, "parse_pending_backlog")
    try:
        rows = (
            db.query(Filing)
            .filter(Filing.status == "pending")
            .order_by(Filing.created_at.asc())
            .limit(batch_size)
            .all()
        )
        ids = [r.id for r in rows]
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()

    parsed = 0
    for fid in ids:
        try:
            from src.etl.doc_parser import parse_and_index_filing

            res = parse_and_index_filing(fid)
            if res.get("status") in ("embedded", "parsed"):
                parsed += 1
        except Exception as exc:
            logger.warning("parse_pending_filings: %s failed: %s", fid, exc)

    db = SessionLocal()
    try:
        _finish_etl_run(db, run, records=parsed, metadata={"considered": len(ids)})
    finally:
        db.close()
    return {"parsed": parsed, "considered": len(ids)}


# ------------------------------------------------------------------ #
#  News ingestion                                                    #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.ingest_news")
def ingest_news(self, *, days: int = 1, limit: int = 200):
    db = SessionLocal()
    run = _log_etl_run(db, "news_ingest")
    try:
        from src.etl.news_ingest import ingest_news_for_universe

        result = ingest_news_for_universe(days=days, per_company_limit=5)
        _finish_etl_run(db, run, records=result.get("stored", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Transcripts                                                       #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.ingest_transcripts")
def ingest_transcripts(self, *, limit: int = 50):
    db = SessionLocal()
    run = _log_etl_run(db, "transcripts_ingest")
    try:
        from src.etl.transcript_ingest import ingest_transcripts_universe

        result = ingest_transcripts_universe(limit=limit)
        _finish_etl_run(db, run, records=result.get("stored", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Social ingestion                                                  #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.ingest_social")
def ingest_social_task(self):
    db = SessionLocal()
    run = _log_etl_run(db, "social_ingest")
    try:
        from src.etl.social_ingest import ingest_social

        result = ingest_social()
        total = sum(int(v) for k, v in result.items() if isinstance(v, int) and k != "indexed")
        _finish_etl_run(db, run, records=total, metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.reap_social")
def reap_social_task(self, *, retention_days: int = 30):
    db = SessionLocal()
    run = _log_etl_run(db, "social_reaper")
    try:
        from src.etl.social_ingest import reap_deleted_posts

        reaped = reap_deleted_posts(retention_days=retention_days)
        _finish_etl_run(db, run, records=reaped, metadata={"reaped": reaped})
        return {"reaped": reaped}
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Macro / commodity                                                 #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.ingest_macro_commodity")
def ingest_macro_commodity(self):
    db = SessionLocal()
    run = _log_etl_run(db, "macro_commodity")
    try:
        from src.etl.macro_ingest import ingest_macro_and_commodities

        result = ingest_macro_and_commodities()
        records = (
            (result.get("fred") or {}).get("observations", 0)
            + (result.get("commodities") or {}).get("observations", 0)
        )
        _finish_etl_run(db, run, records=records, metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Theme tagging / event extraction / insight discovery              #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.tag_themes")
def tag_themes(self, *, limit: int = 200):
    db = SessionLocal()
    run = _log_etl_run(db, "theme_tagging")
    try:
        from src.agents.etl_agents import ThemeTaggingAgent

        result = ThemeTaggingAgent().tag_universe(limit=limit)
        _finish_etl_run(db, run, records=result.get("themes_applied", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.extract_events")
def extract_events(self):
    db = SessionLocal()
    run = _log_etl_run(db, "event_extraction")
    try:
        from src.agents.etl_agents import EventExtractionAgent

        result = EventExtractionAgent().run()
        _finish_etl_run(db, run, records=result.get("events_created", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.compute_daily_insights")
def compute_daily_insights(self, *, max_insights: int = 25):
    db = SessionLocal()
    run = _log_etl_run(db, "insight_discovery")
    try:
        from src.agents.etl_agents import InsightDiscoveryAgent

        result = InsightDiscoveryAgent(max_insights=max_insights).run()
        _finish_etl_run(db, run, records=result.get("created", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.revalidate_insights")
def revalidate_insights(self):
    db = SessionLocal()
    run = _log_etl_run(db, "insight_revalidation")
    try:
        from src.agents.etl_agents import InsightRevalidationAgent

        result = InsightRevalidationAgent().run()
        _finish_etl_run(db, run, records=result.get("evaluated", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Phase 2: Knowledge graph                                          #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.backfill_graph_edges")
def backfill_graph_edges_task(self):
    """Bootstrap relation_edges from existing structured data."""
    db = SessionLocal()
    run = _log_etl_run(db, "graph_backfill")
    try:
        from src.agents.etl_agents import backfill_graph_edges

        result = backfill_graph_edges()
        total = sum(result.get("created", {}).values())
        _finish_etl_run(db, run, records=total, metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.mine_supply_chain")
def mine_supply_chain(self):
    db = SessionLocal()
    run = _log_etl_run(db, "supply_chain_mining")
    try:
        from src.agents.etl_agents import SupplyChainAgent

        result = SupplyChainAgent().run()
        _finish_etl_run(db, run, records=result.get("edges_created", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, name="etl.mine_patterns")
def mine_patterns(self):
    db = SessionLocal()
    run = _log_etl_run(db, "pattern_mining")
    try:
        from src.agents.etl_agents import PatternMiningAgent

        result = PatternMiningAgent().run()
        _finish_etl_run(db, run, records=result.get("insights_created", 0), metadata=result)
        return result
    except Exception as e:
        _finish_etl_run(db, run, status="failed", error=str(e))
        raise
    finally:
        db.close()


# ------------------------------------------------------------------ #
#  Seeding                                                           #
# ------------------------------------------------------------------ #


@app.task(bind=True, name="etl.seed_static_tables")
def seed_static_tables(self):
    """Run all bootstrap seeders (themes, sector-commodity links, source quality)."""
    from src.etl.confidence import seed_source_quality
    from src.etl.sector_commodity_loader import seed_sector_commodity_links
    from src.etl.theme_taxonomy_loader import seed_theme_taxonomy

    return {
        "themes": seed_theme_taxonomy(),
        "sector_commodity_links": seed_sector_commodity_links(),
        "source_quality": seed_source_quality(),
    }


# ------------------------------------------------------------------ #
#  Full company refresh (on-demand)                                  #
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
