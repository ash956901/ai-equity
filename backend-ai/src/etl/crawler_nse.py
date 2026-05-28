"""NSE filings crawler.

NSE India requires session cookies and specific headers for scraping.
This implementation fetches corporate announcements via the NSE API.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import requests

from src.etl.crawler_base import BaseCrawler

logger = logging.getLogger(__name__)

NSE_CORPORATE_ANNOUNCEMENTS = "https://www.nseindia.com/api/corporate-announcements"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
}


class NSECrawler(BaseCrawler):
    """Crawler for NSE corporate filings."""

    def __init__(self):
        super().__init__("https://www.nseindia.com")
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """Get a session with NSE cookies."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(NSE_HEADERS)
            try:
                self._session.get("https://www.nseindia.com", timeout=10)
            except Exception as e:
                logger.warning("Failed to initialize NSE session: %s", e)
        return self._session

    def crawl(
        self,
        company_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        since_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Crawl NSE corporate announcements.

        Args:
            company_id: Ignored for direct NSE crawl (use symbol instead).
            symbol: NSE symbol to filter (e.g. "RELIANCE").
            since_date: Date string YYYY-MM-DD to filter from.

        Returns:
            List of announcement metadata dicts.
        """
        session = self._get_session()
        params: Dict[str, str] = {"index": "equities"}
        if symbol:
            params["symbol"] = symbol
        if since_date:
            params["from_date"] = since_date

        try:
            resp = session.get(
                NSE_CORPORATE_ANNOUNCEMENTS,
                params=params,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("NSE API returned status %d", resp.status_code)
                return []

            data = resp.json()
            items = data if isinstance(data, list) else data.get("data", data.get("results", []))
            results = []
            for item in items[:50]:
                attach_file = item.get("attchmntFile", "")
                attachment_url = (
                    f"https://nsearchives.nseindia.com/corporate/{attach_file}"
                    if attach_file else ""
                )
                results.append({
                    "symbol": item.get("symbol", ""),
                    "subject": item.get("desc", item.get("subject", "")),
                    "filing_type": item.get("subcatdesc") or item.get("desc") or "announcement",
                    "date": item.get("an_dt", item.get("dt", "")),
                    "attachment_url": attachment_url,
                    "source": "NSE",
                })
            logger.info("NSE crawler fetched %d announcements", len(results))
            return results

        except Exception as e:
            logger.error("NSE crawl failed: %s", e)
            return []
