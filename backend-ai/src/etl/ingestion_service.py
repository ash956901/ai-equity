"""Service for ingesting and downloading documents from crawlers.

Handles two ingestion modes:
  1. Document-based (NSE/BSE/SEBI/Screener) — download file, persist to disk, create Filing record
  2. Structured-data (AMFI, mfapi, RBI, Bhavcopy, News RSS) — persist JSON directly to DB tables
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from src.db.models import Company, Filing, NewsArticle
from src.config import get_settings

logger = logging.getLogger(__name__)

FILINGS_DIR = Path("uploads/filings")
FILINGS_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = Path("uploads/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


class DocumentIngestionService:
    """Handles downloading and persisting filing documents."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def ingest_filing(
        self,
        company_id: UUID,
        metadata: Dict[str, Any],
    ) -> Optional[Filing]:
        """Download and persist a filing from crawler metadata."""
        source_url = metadata.get("attachment_url") or metadata.get("url")
        if not source_url:
            logger.warning("No URL found for filing: %s", metadata.get("subject"))
            return None

        # 1. Check if already exists by source_url or title
        existing = (
            self.db.query(Filing)
            .filter(
                Filing.company_id == company_id,
                Filing.source_url == source_url,
            )
            .first()
        )
        if existing:
            return existing

        # 2. Download the file
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            resp = session.get(
                source_url,
                timeout=45,  # Increased timeout
                headers={"User-Agent": "EquityResearchBot/1.0"},
                stream=True,
            )
            if resp.status_code != 200:
                logger.warning("Failed to download filing from %s: %d", source_url, resp.status_code)
                return None

            content = resp.content
            if not content:
                logger.warning("Empty content from %s", source_url)
                return None
                
            doc_hash = hashlib.sha256(content).hexdigest()

            # 3. Check if hash already exists (deduplication)
            existing_hash = (
                self.db.query(Filing)
                .filter(Filing.document_hash == doc_hash)
                .first()
            )
            if existing_hash:
                logger.info("Filing with hash %s already exists", doc_hash)
                return existing_hash

            # 4. Save to filesystem
            filename = os.path.basename(source_url) or "document.pdf"
            if not filename.endswith((".pdf", ".pptx", ".ppt", ".txt", ".csv", ".xlsx")):
                filename += ".pdf"  # Default assumption for filings

            safe_name = f"{doc_hash[:16]}_{filename}"
            file_path = FILINGS_DIR / safe_name
            
            with open(file_path, "wb") as f:
                f.write(content)

            # 5. Create Filing record
            filing_date_str = metadata.get("date")
            try:
                filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").date() if filing_date_str else datetime.utcnow().date()
            except ValueError:
                filing_date = datetime.utcnow().date()

            filing = Filing(
                company_id=company_id,
                filing_type=metadata.get("filing_type", "announcement"),
                title=metadata.get("subject", metadata.get("title", "Filing")),
                filing_date=filing_date,
                source_url=source_url,
                raw_uri=str(file_path),
                document_hash=doc_hash,
                status="downloaded",
                metadata_=metadata,
            )
            self.db.add(filing)
            self.db.commit()
            self.db.refresh(filing)
            
            logger.info("Ingested filing: %s for company %s", filing.title, company_id)
            return filing

        except Exception as e:
            logger.error("Error ingesting filing from %s: %s", source_url, e)
            return None

    # ------------------------------------------------------------------
    # Structured data ingestion (no file download)
    # ------------------------------------------------------------------

    def ingest_screener_data(
        self,
        company_id: UUID,
        screener_data: Dict[str, Any],
    ) -> int:
        """Persist screener.in financials as Filing + JSON blob.

        Stores the full screener result (P&L, BS, CF, ratios, etc.) as a
        single Filing record with filing_type='screener_snapshot' and the
        JSON data in metadata_.

        Returns number of records created (0 or 1).
        """
        symbol = screener_data.get("symbol", "")
        content_hash = hashlib.sha256(
            json.dumps(screener_data, sort_keys=True, default=str).encode()
        ).hexdigest()

        existing = (
            self.db.query(Filing)
            .filter(Filing.document_hash == content_hash)
            .first()
        )
        if existing:
            return 0

        # Save JSON to disk as well for the document processor
        json_path = DATA_DIR / f"screener_{symbol}_{content_hash[:12]}.json"
        with open(json_path, "w") as f:
            json.dump(screener_data, f, indent=2, default=str)

        filing = Filing(
            company_id=company_id,
            filing_type="screener_snapshot",
            title=f"Screener.in snapshot — {symbol}",
            filing_date=datetime.utcnow().date(),
            source_url=screener_data.get("url", ""),
            raw_uri=str(json_path),
            document_hash=content_hash,
            status="downloaded",
            metadata_=screener_data.get("meta", {}),
        )
        self.db.add(filing)
        self.db.commit()
        logger.info("Ingested screener snapshot for %s", symbol)
        return 1

    def ingest_news_articles(
        self,
        articles: List[Dict[str, Any]],
    ) -> int:
        """Persist news RSS articles to the news_articles table.

        Deduplicates by source_url.
        Returns number of new articles created.
        """
        created = 0
        for article in articles:
            link = article.get("link", "")
            if not link:
                continue

            existing = (
                self.db.query(NewsArticle)
                .filter(NewsArticle.source_url == link)
                .first()
            )
            if existing:
                continue

            pub_date_str = article.get("pub_date") or article.get("pub_date_raw", "")
            try:
                pub_dt = datetime.fromisoformat(pub_date_str) if pub_date_str else datetime.utcnow()
            except (ValueError, TypeError):
                pub_dt = datetime.utcnow()

            news = NewsArticle(
                headline=article.get("title", ""),
                body=article.get("description", ""),
                source=article.get("feed_name", article.get("source", "")),
                source_url=link,
                published_at=pub_dt,
            )
            self.db.add(news)
            created += 1

        if created:
            self.db.commit()
        logger.info("Ingested %d new news articles (skipped %d dupes)", created, len(articles) - created)
        return created

    def ingest_structured_data(
        self,
        pipeline_name: str,
        data: Any,
    ) -> int:
        """Persist arbitrary structured data as a JSON file on disk.

        Used for AMFI NAVs, mfapi results, RBI macro, bhavcopy, data.gov
        datasets — data that doesn't map to a single company Filing.

        Returns number of records in the saved blob.
        """
        if not data:
            return 0

        records = data if isinstance(data, list) else [data]
        content_hash = hashlib.sha256(
            json.dumps(records[:5], sort_keys=True, default=str).encode()
        ).hexdigest()[:12]

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        json_path = DATA_DIR / f"{pipeline_name}_{timestamp}_{content_hash}.json"

        with open(json_path, "w") as f:
            json.dump(records, f, indent=2, default=str)

        logger.info(
            "Saved %d %s records to %s",
            len(records), pipeline_name, json_path,
        )
        return len(records)
