"""Investor relations site crawler.

Auto-discovers IR pages, walks them for PDF/PPTX links, downloads each
document, deduplicates by SHA-256, and persists ``Filing`` rows. Returns
the list of newly created filings so the Celery task can chain parsing.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from uuid import UUID

import requests
from bs4 import BeautifulSoup

from src.db.database import SessionLocal
from src.db.models import Company, Filing
from src.etl.crawler_base import BaseCrawler
from src.etl.crawler_nse import _detect_filing_type
from src.etl.guardrails import RateLimiter, can_fetch, is_source_disabled
from src.etl.source_registry import get_source
from src.etl.storage import store_bytes

logger = logging.getLogger(__name__)

SOURCE_NAME = "ir_pages"
USER_AGENT = "EquityResearchBot/1.0 (+contact via repo issues)"

COMMON_IR_PATHS = [
    "/investor-relations",
    "/investors",
    "/financials",
    "/ir",
    "/investor",
    "/shareholders",
    "/corporate/investors",
    "/about-us/investors",
]


def _is_valid_ir_page(content: str) -> bool:
    content_lower = content.lower()
    keywords = [
        "investor relations",
        "financial results",
        "annual report",
        "quarterly results",
        "investor presentation",
    ]
    return sum(1 for kw in keywords if kw in content_lower) >= 2


class IRCrawler(BaseCrawler):
    """Crawler for company investor relations pages."""

    def __init__(self):
        super().__init__("")
        cfg = get_source("filings", SOURCE_NAME) or {}
        rpm = int(cfg.get("quota_rpm", 12))
        burst = int(cfg.get("quota_burst", rpm * 2))
        self._limiter = RateLimiter(SOURCE_NAME, rpm=rpm, burst=burst)

    def discover_ir_url(self, company: Company) -> Optional[str]:
        base_domain = company.website_domain
        if not base_domain:
            return None
        base_domain = base_domain.replace("https://", "").replace("http://", "").strip("/")
        base_url = f"https://{base_domain}"

        for path in COMMON_IR_PATHS:
            url = base_url + path
            if not can_fetch(url, USER_AGENT):
                continue
            if not self._limiter.acquire(timeout=5.0):
                continue
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": USER_AGENT})
            except Exception:
                continue
            if resp.status_code == 200 and _is_valid_ir_page(resp.text):
                return url
        return None

    def _download(self, url: str) -> Optional[bytes]:
        if not can_fetch(url, USER_AGENT):
            logger.info("robots.txt blocks %s", url)
            return None
        if not self._limiter.acquire(timeout=10.0):
            return None
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return None
            return resp.content
        except Exception as exc:
            logger.warning("IR download failed for %s: %s", url, exc)
            return None

    def crawl(
        self,
        company_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        since_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Crawl IR pages, persist new filings, return summaries."""
        if is_source_disabled(SOURCE_NAME):
            logger.info("IR crawler muted via kill switch")
            return []

        results: List[Dict[str, Any]] = []
        db = SessionLocal()
        try:
            if company_id:
                companies = db.query(Company).filter(Company.id == company_id).all()
            else:
                companies = (
                    db.query(Company)
                    .filter(Company.listing_status == "active")
                    .filter(Company.website_domain.isnot(None))
                    .limit(50)
                    .all()
                )

            for company in companies:
                ir_url = company.ir_page_url or self.discover_ir_url(company)
                if ir_url and company.ir_page_url != ir_url:
                    company.ir_page_url = ir_url
                    db.commit()
                if not ir_url:
                    continue
                if not self._limiter.acquire(timeout=5.0):
                    continue

                try:
                    resp = requests.get(ir_url, timeout=15, headers={"User-Agent": USER_AGENT})
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                except Exception as exc:
                    logger.warning("IR fetch failed for %s: %s", ir_url, exc)
                    continue

                doc_links: List[Dict[str, str]] = []
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if re.search(r"\.(pdf|pptx?)$", href, re.I):
                        full_url = href if href.startswith("http") else urljoin(ir_url, href)
                        doc_links.append(
                            {
                                "url": full_url,
                                "title": link.get_text(strip=True) or "Document",
                            }
                        )
                doc_links = doc_links[:20]

                for doc in doc_links:
                    doc_bytes = self._download(doc["url"])
                    if doc_bytes is None:
                        continue
                    document_hash = hashlib.sha256(doc_bytes).hexdigest()
                    existing = (
                        db.query(Filing).filter(Filing.document_hash == document_hash).first()
                    )
                    if existing:
                        continue
                    ext = "pdf" if doc["url"].lower().endswith(".pdf") else "pptx"
                    raw_uri = store_bytes(
                        f"filings/{company.id}",
                        f"{document_hash}.{ext}",
                        doc_bytes,
                    )
                    filing = Filing(
                        company_id=company.id,
                        filing_type=_detect_filing_type(doc["title"]),
                        title=doc["title"],
                        filing_date=date.today(),
                        source_url=doc["url"],
                        raw_uri=raw_uri,
                        document_hash=document_hash,
                        status="pending",
                        metadata_={"source": "IR", "domain": company.website_domain},
                    )
                    db.add(filing)
                    db.flush()
                    results.append(
                        {
                            "filing_id": str(filing.id),
                            "company_id": str(company.id),
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
        logger.info("IR crawler persisted %d new filings", len(results))
        return results
