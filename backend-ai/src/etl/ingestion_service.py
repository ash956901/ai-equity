"""Service for ingesting and downloading documents from crawlers."""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from src.db.models import Company, Filing
from src.config import get_settings

logger = logging.getLogger(__name__)

FILINGS_DIR = Path("uploads/filings")
FILINGS_DIR.mkdir(parents=True, exist_ok=True)


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
