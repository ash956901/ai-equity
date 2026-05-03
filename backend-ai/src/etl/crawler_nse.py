"""NSE filings crawler.

Fetches corporate announcements from NSE, downloads the attached document,
deduplicates by SHA-256, persists a ``Filing`` row and stores raw bytes via
``src.etl.storage``. Returns the list of newly created filing IDs so the
Celery task can chain document parsing.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from uuid import UUID

import requests

from src.db.database import SessionLocal
from src.db.models import Company, Filing
from src.etl.crawler_base import BaseCrawler
from src.etl.guardrails import RateLimiter, can_fetch, is_source_disabled
from src.etl.source_registry import get_source
from src.etl.storage import store_bytes

logger = logging.getLogger(__name__)

NSE_CORPORATE_ANNOUNCEMENTS = "https://www.nseindia.com/api/corporate-announcements"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
}
NSE_DOC_USER_AGENT = "EquityResearchBot/1.0 (+contact via repo issues)"
SOURCE_NAME = "nse_announcements"


def _detect_filing_type(title: str) -> str:
    title_lower = (title or "").lower()
    if "annual report" in title_lower:
        return "Annual_Report"
    if "quarterly result" in title_lower or re.search(r"\bq[1-4]\b", title_lower):
        return "Quarterly_Results"
    if "investor presentation" in title_lower or "earnings presentation" in title_lower:
        return "Presentation"
    if "concall" in title_lower or "earnings call" in title_lower or "transcript" in title_lower:
        return "Concall"
    if "press release" in title_lower:
        return "Press_Release"
    if "shareholding pattern" in title_lower:
        return "Shareholding_Pattern"
    return "Announcement"


def _parse_date(raw: str) -> Optional[date]:
    if not raw:
        return None
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


class NSECrawler(BaseCrawler):
    """Crawler for NSE corporate filings with persistence + dedup."""

    def __init__(self):
        super().__init__("https://www.nseindia.com")
        self._session: Optional[requests.Session] = None
        cfg = get_source("filings", SOURCE_NAME) or {}
        rpm = int(cfg.get("quota_rpm", 30))
        burst = int(cfg.get("quota_burst", rpm * 2))
        self._limiter = RateLimiter(SOURCE_NAME, rpm=rpm, burst=burst)

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(NSE_HEADERS)
            try:
                self._session.get("https://www.nseindia.com", timeout=10)
            except Exception as exc:
                logger.warning("Failed to initialize NSE session: %s", exc)
        return self._session

    def _fetch_announcements(
        self, symbol: Optional[str], since_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        if not self._limiter.acquire(timeout=10.0):
            logger.warning("NSE rate limit exceeded; skipping fetch")
            return []
        params: Dict[str, str] = {"index": "equities"}
        if symbol:
            params["symbol"] = symbol
        if since_date:
            params["from_date"] = since_date
        session = self._get_session()
        try:
            resp = session.get(NSE_CORPORATE_ANNOUNCEMENTS, params=params, timeout=15)
        except Exception as exc:
            logger.error("NSE list fetch failed: %s", exc)
            return []
        if resp.status_code != 200:
            logger.warning("NSE list returned %d", resp.status_code)
            return []
        try:
            data = resp.json()
        except ValueError:
            return []
        items = data if isinstance(data, list) else data.get("data", data.get("results", []))
        return list(items or [])

    def _download_document(self, url: str) -> Optional[bytes]:
        if not url:
            return None
        if not can_fetch(url, NSE_DOC_USER_AGENT):
            logger.info("robots.txt blocks %s", url)
            return None
        if not self._limiter.acquire(timeout=10.0):
            logger.warning("NSE rate-limited document fetch %s", url)
            return None
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": NSE_DOC_USER_AGENT, "Referer": "https://www.nseindia.com/"},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning("NSE doc %s returned %d", url, resp.status_code)
                return None
            return resp.content
        except Exception as exc:
            logger.error("NSE doc download failed (%s): %s", url, exc)
            return None

    def _resolve_company_ids(
        self, db, company_id: Optional[UUID], symbol: Optional[str]
    ) -> Dict[str, UUID]:
        """Return a {symbol_upper: company_id} map for resolving announcements."""
        out: Dict[str, UUID] = {}
        query = db.query(Company)
        if company_id:
            company = query.filter(Company.id == company_id).first()
            if company and company.ticker_nse:
                out[company.ticker_nse.upper()] = company.id
            return out
        if symbol:
            company = query.filter(Company.ticker_nse == symbol.upper()).first()
            if company:
                out[symbol.upper()] = company.id
            return out
        for company in query.filter(Company.listing_status == "active").limit(2000).all():
            if company.ticker_nse:
                out[company.ticker_nse.upper()] = company.id
        return out

    def crawl(
        self,
        company_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        since_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Crawl NSE corporate announcements, persist new filings.

        Returns a list of dicts {filing_id, symbol, title, source_url} for new
        filings only (skips duplicates).
        """
        if is_source_disabled(SOURCE_NAME):
            logger.info("NSE crawler muted via kill switch")
            return []

        items = self._fetch_announcements(symbol, since_date)
        if not items:
            return []

        results: List[Dict[str, Any]] = []
        db = SessionLocal()
        try:
            company_map = self._resolve_company_ids(db, company_id, symbol)
            for item in items[:100]:
                sym = (item.get("symbol") or "").upper().strip()
                if not sym or sym not in company_map:
                    continue
                title = item.get("desc") or item.get("subject") or ""
                attachment_url = item.get("attchmntFile") or item.get("attachmentFile") or ""
                if attachment_url and attachment_url.startswith("/"):
                    attachment_url = urljoin("https://www.nseindia.com", attachment_url)
                doc_bytes = self._download_document(attachment_url) if attachment_url else None
                if doc_bytes is None:
                    continue

                document_hash = hashlib.sha256(doc_bytes).hexdigest()
                existing = db.query(Filing).filter(Filing.document_hash == document_hash).first()
                if existing:
                    continue

                ext = "pdf" if attachment_url.lower().endswith(".pdf") else (
                    "pptx" if attachment_url.lower().endswith(".pptx") else "bin"
                )
                cid = company_map[sym]
                raw_uri = store_bytes(
                    f"filings/{cid}",
                    f"{document_hash}.{ext}",
                    doc_bytes,
                    content_type="application/pdf" if ext == "pdf" else None,
                )

                filing = Filing(
                    company_id=cid,
                    filing_type=_detect_filing_type(title),
                    title=title or "NSE Announcement",
                    filing_date=_parse_date(item.get("an_dt") or item.get("dt") or "")
                    or date.today(),
                    source_url=attachment_url,
                    raw_uri=raw_uri,
                    document_hash=document_hash,
                    status="pending",
                    metadata_={
                        "source": "NSE",
                        "symbol": sym,
                        "raw_meta": {k: v for k, v in item.items() if isinstance(v, (str, int, float, bool))},
                    },
                )
                db.add(filing)
                db.flush()
                results.append(
                    {
                        "filing_id": str(filing.id),
                        "symbol": sym,
                        "title": filing.title,
                        "source_url": filing.source_url,
                        "filing_type": filing.filing_type,
                    }
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        logger.info("NSE crawler persisted %d new filings", len(results))
        return results
