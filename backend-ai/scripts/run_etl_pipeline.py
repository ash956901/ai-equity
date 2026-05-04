"""Run all ETL pipelines manually (without Celery).

Usage:
    python scripts/run_etl_pipeline.py              # Run all pipelines
    python scripts/run_etl_pipeline.py --quick       # Run fast pipelines only (no Celery)
    python scripts/run_etl_pipeline.py --pipeline X  # Run a specific pipeline
"""

import sys
import os
import argparse
import logging
import time

sys.path.append(os.getcwd())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
# Suppress noisy urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)


PIPELINES = [
    "bhavcopy",
    "amfi",
    "news_rss",
    "rbi",
    "datagov",
    "sebi",
    "screener",
    "mfapi",
]


def run_bhavcopy():
    """NSE Bhavcopy — daily OHLCV for all equities."""
    from src.etl.crawler_nse_bhavcopy import NSEBhavcopycrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = NSEBhavcopycrawler()
    data = crawler.crawl()

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("nse_bhavcopy", data)
        return {"source": "NSE_Bhavcopy", "records": count, "date": data[0].get("date") if data else "N/A"}
    finally:
        db.close()


def run_amfi():
    """AMFI NAV — daily mutual fund NAVs."""
    from src.etl.crawler_amfi import AMFICrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = AMFICrawler()
    data = crawler.crawl()

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("amfi_nav", data)
        return {"source": "AMFI", "schemes": count}
    finally:
        db.close()


def run_news_rss():
    """News RSS — ET Markets + LiveMint articles."""
    from src.etl.crawler_news_rss import NewsRSSCrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = NewsRSSCrawler()
    articles = crawler.crawl()

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        created = ingestion.ingest_news_articles(articles)
        return {"source": "RSS", "fetched": len(articles), "new": created}
    finally:
        db.close()


def run_rbi():
    """RBI macro — policy rates, M3, reserves."""
    from src.etl.crawler_rbi import RBICrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = RBICrawler()
    data = crawler.crawl()

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("rbi_macro", data)
        return {
            "source": "RBI",
            "indicators": len(data.get("policy_rates", {})),
            "table_rows": len(data.get("key_rates_table", [])),
        }
    finally:
        db.close()


def run_datagov():
    """data.gov.in — MCA dataset discovery."""
    from src.etl.crawler_datagov import DataGovCrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = DataGovCrawler()
    data = crawler.discover_datasets()

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("datagov_mca", data)
        return {"source": "data.gov.in", "datasets": count}
    finally:
        db.close()


def run_sebi():
    """SEBI/NSE+BSE filings — corporate announcements."""
    from src.etl.crawler_sebi import SEBICrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = SEBICrawler()
    data = crawler.crawl(since_date="2024-01-01")

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("sebi_filings", data)
        return {"source": "SEBI", "filings": count}
    finally:
        db.close()


def run_screener():
    """Screener.in — 10-year financials for sample companies."""
    from src.etl.crawler_screener import ScreenerCrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = ScreenerCrawler()

    # Test with a couple of companies
    symbols = ["RELIANCE", "TCS"]
    results = []
    for sym in symbols:
        data = crawler.crawl(sym)
        if data.get("profit_loss", {}).get("data"):
            results.append(data)

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("screener", results)
        return {"source": "screener.in", "companies": len(results), "records": count}
    finally:
        db.close()


def run_mfapi():
    """mfapi.in — MF NAV history."""
    from src.etl.crawler_mfapi import MFApiCrawler
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.database import SessionLocal

    crawler = MFApiCrawler()
    data = crawler.crawl(limit=3)  # Small batch for testing

    db = SessionLocal()
    try:
        ingestion = DocumentIngestionService(db)
        count = ingestion.ingest_structured_data("mfapi", data)
        return {"source": "mfapi.in", "schemes": count}
    finally:
        db.close()


RUNNERS = {
    "bhavcopy": run_bhavcopy,
    "amfi": run_amfi,
    "news_rss": run_news_rss,
    "rbi": run_rbi,
    "datagov": run_datagov,
    "sebi": run_sebi,
    "screener": run_screener,
    "mfapi": run_mfapi,
}


def run_pipeline(pipelines=None):
    if pipelines is None:
        pipelines = PIPELINES

    logger.info("=" * 60)
    logger.info("  ETL Pipeline — %d sources", len(pipelines))
    logger.info("=" * 60)

    results = {}
    for i, name in enumerate(pipelines, 1):
        logger.info("\n[%d/%d] Running: %s", i, len(pipelines), name.upper())
        start = time.monotonic()
        try:
            runner = RUNNERS.get(name)
            if runner is None:
                logger.warning("  Unknown pipeline: %s — skipping", name)
                results[name] = {"status": "skipped"}
                continue

            result = runner()
            elapsed = time.monotonic() - start
            logger.info("  ✅ %s — %.1fs — %s", name, elapsed, result)
            results[name] = {"status": "ok", "elapsed": round(elapsed, 1), **result}
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("  ❌ %s — %.1fs — %s", name, elapsed, e)
            results[name] = {"status": "failed", "elapsed": round(elapsed, 1), "error": str(e)}

    logger.info("\n" + "=" * 60)
    logger.info("  SUMMARY")
    logger.info("=" * 60)
    for name, res in results.items():
        icon = "✅" if res["status"] == "ok" else "❌" if res["status"] == "failed" else "⚠️"
        logger.info("  %s %-12s %s", icon, name, res)

    passed = sum(1 for r in results.values() if r["status"] == "ok")
    logger.info("\n  %d/%d pipelines passed", passed, len(results))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ETL pipelines")
    parser.add_argument("--pipeline", "-p", help="Run a specific pipeline", choices=PIPELINES)
    parser.add_argument("--quick", "-q", action="store_true", help="Run only fast pipelines (bhavcopy, amfi, rss, rbi)")
    args = parser.parse_args()

    if args.pipeline:
        run_pipeline([args.pipeline])
    elif args.quick:
        run_pipeline(["bhavcopy", "amfi", "news_rss", "rbi"])
    else:
        run_pipeline()
