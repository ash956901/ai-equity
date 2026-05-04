"""mfapi.in crawler (open-source MF data API).

Provides:
  - List of all schemes: GET https://api.mfapi.in/mf
  - Scheme NAV history:  GET https://api.mfapi.in/mf/{scheme_code}
  - Latest NAV:          GET https://api.mfapi.in/mf/{scheme_code}/latest

Response shape (scheme detail):
  {
    "meta": { "fund_house": "...", "scheme_type": "...", "scheme_category": "...",
              "scheme_code": 119551, "scheme_name": "..." },
    "data": [ { "date": "02-05-2026", "nav": "104.5706" }, ... ]
  }
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.mfapi.in/mf"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class MFApiCrawler:
    """Crawler for mfapi.in — open-source mutual fund NAV history & metadata.

    Usage:
        crawler = MFApiCrawler()

        # List all ~45,000 schemes
        schemes = crawler.list_schemes()

        # Get NAV history for a specific scheme
        detail = crawler.get_scheme_detail(119551)

        # Crawl NAV history for multiple schemes
        results = crawler.crawl(scheme_codes=[119551, 100027])
    """

    def __init__(self, delay: float = 0.5):
        """
        Args:
            delay: Seconds between API calls to be respectful.
        """
        self.delay = delay
        self._session: Optional[requests.Session] = None
        self._last_request: float = 0.0

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = _build_session()
        return self._session

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _get_json(self, url: str) -> Any:
        self._throttle()
        try:
            resp = self.session.get(url, timeout=30)
            self._last_request = time.monotonic()
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("mfapi fetch failed (%s): %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def list_schemes(self) -> List[Dict[str, Any]]:
        """Return list of all MF schemes [{schemeCode, schemeName}, ...].

        Warning: response is ~5 MB — cache this.
        """
        data = self._get_json(BASE_URL)
        if data is None:
            return []
        logger.info("mfapi: listed %d schemes", len(data))
        return data

    def get_scheme_detail(self, scheme_code: int) -> Optional[Dict[str, Any]]:
        """Fetch full NAV history + meta for a single scheme.

        Returns:
            { "meta": { fund_house, scheme_type, scheme_category, scheme_code, scheme_name },
              "data": [ { "date": "02-05-2026", "nav": "104.5706" }, ... ] }
        """
        data = self._get_json(f"{BASE_URL}/{scheme_code}")
        if data is None:
            return None
        logger.info(
            "mfapi: fetched %d NAV records for scheme %d",
            len(data.get("data", [])), scheme_code,
        )
        return data

    def get_latest_nav(self, scheme_code: int) -> Optional[Dict[str, Any]]:
        """Fetch latest NAV for a single scheme."""
        return self._get_json(f"{BASE_URL}/{scheme_code}/latest")

    def crawl(
        self,
        scheme_codes: Optional[List[int]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Crawl NAV history for multiple schemes.

        Args:
            scheme_codes: Specific codes to fetch. If None, fetches first `limit`
                          schemes from the master list.
            limit:        Max schemes to fetch when scheme_codes is None.

        Returns:
            List of scheme detail dicts (meta + data).
        """
        if scheme_codes is None:
            all_schemes = self.list_schemes()
            scheme_codes = [s["schemeCode"] for s in all_schemes[:limit]]

        results: List[Dict[str, Any]] = []
        for code in scheme_codes:
            detail = self.get_scheme_detail(code)
            if detail and detail.get("data"):
                detail["source"] = "mfapi.in"
                results.append(detail)
            else:
                logger.warning("Empty/failed for scheme %d — skipping", code)

        logger.info("mfapi crawler: fetched %d / %d schemes", len(results), len(scheme_codes))
        return results
