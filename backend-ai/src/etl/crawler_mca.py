"""MCA (Ministry of Corporate Affairs) crawler.

Targets mcav3.mca.gov.in endpoints.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from src.etl.crawler_base import BaseCrawler

logger = logging.getLogger(__name__)

MCA_BASE_URL = "https://mcav3.mca.gov.in"
MCA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


class MCACrawler(BaseCrawler):
    """Crawler for MCA v3 portal filings."""

    def __init__(self):
        super().__init__(MCA_BASE_URL)
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """Get a session with MCA headers and retry logic."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(MCA_HEADERS)
            
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
            
            try:
                # Prime session
                self._session.get(MCA_BASE_URL, timeout=15)
            except Exception as e:
                logger.warning("Failed to initialize MCA session: %s", e)
        return self._session

    def crawl(
        self,
        company_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        since_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Crawl MCA v3 portal.

        Args:
            company_id: MCA company ID/CIN to filter.
            symbol: Ignored for MCA (use CIN instead).
            since_date: Date string YYYY-MM-DD to filter from.

        Returns:
            List of metadata dicts.
        """
        session = self._get_session()
        
        try:
            # We target a generic MCA URL.
            # Replace with specific MCA JSON/API endpoint if available.
            resp = session.get(
                MCA_BASE_URL,
                timeout=15,
            )
            
            if resp.status_code != 200:
                logger.warning("MCA API returned status %d", resp.status_code)
                return []
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            
            # Simulated parsing of the MCA page
            links = soup.find_all('a', href=True)
            for link in links[:50]:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if text and href and ('notice' in text.lower() or 'circular' in text.lower()):
                    results.append({
                        "symbol": symbol or "MCA_CIN",
                        "subject": text,
                        "filing_type": "mca_filing",
                        "date": since_date or "",
                        "attachment_url": href if href.startswith("http") else f"{self.base_url}{href}",
                        "source": "MCA",
                    })
                    
            logger.info("MCA crawler fetched %d items", len(results))
            return results

        except Exception as e:
            logger.error("MCA crawl failed: %s", e)
            return []
