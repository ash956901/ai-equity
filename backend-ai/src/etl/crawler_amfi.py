"""AMFI NAV crawler.

Fetches all mutual fund NAVs from the official AMFI India text file.
Source: https://www.amfiindia.com/spages/NAVAll.txt

Format (semicolon-delimited, grouped by fund house / category):
  Line 1:  "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date"
  Blank / category header lines are interspersed.
  Data lines: "119551;INF209KA12Z1;INF209KA13Z9;Aditya Birla Sun Life Banking...;104.5706;30-Apr-2026"

This crawler returns ~14,000+ scheme records per invocation.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
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


class AMFICrawler:
    """Crawler for AMFI India daily NAV data (~14,000+ schemes).

    Usage:
        crawler = AMFICrawler()
        data = crawler.crawl()
        # data = [{"scheme_code": "119551", "scheme_name": "...", "nav": 104.57, ...}, ...]
    """

    def __init__(self):
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = _build_session()
        return self._session

    def crawl(
        self,
        scheme_code: Optional[str] = None,
        fund_house: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all NAVs from AMFI.

        Args:
            scheme_code: Filter to a single scheme code (e.g. "119551").
            fund_house:  Filter by fund house name substring (case-insensitive).

        Returns:
            List of dicts with keys:
                scheme_code, isin_growth, isin_div_reinvest, scheme_name,
                nav, date, fund_house, category, source
        """
        try:
            resp = self.session.get(AMFI_NAV_URL, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("AMFI fetch failed: %s", exc)
            return []

        raw_text = resp.text
        return self._parse(raw_text, scheme_code, fund_house)

    def _parse(
        self,
        text: str,
        scheme_code_filter: Optional[str],
        fund_house_filter: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Parse the AMFI NAVAll.txt text format."""
        lines = text.strip().split("\n")
        results: List[Dict[str, Any]] = []

        current_category = ""
        current_fund_house = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Header row — skip
            if line.startswith("Scheme Code"):
                continue

            # Category header: "Open Ended Schemes(Debt Scheme - Banking and PSU Fund)"
            if line.startswith("Open Ended") or line.startswith("Close Ended") or line.startswith("Interval Fund"):
                current_category = line
                continue

            # Fund house header: standalone name without semicolons
            if ";" not in line:
                current_fund_house = line
                continue

            # Data line
            parts = line.split(";")
            if len(parts) < 6:
                continue

            code = parts[0].strip()
            isin_growth = parts[1].strip() if parts[1].strip() != "-" else None
            isin_div = parts[2].strip() if parts[2].strip() != "-" else None
            name = parts[3].strip()
            nav_str = parts[4].strip()
            nav_date = parts[5].strip()

            # Filters
            if scheme_code_filter and code != scheme_code_filter:
                continue
            if fund_house_filter and fund_house_filter.lower() not in current_fund_house.lower():
                continue

            try:
                nav = float(nav_str)
            except ValueError:
                nav = None  # N.A. or "N/A"

            results.append({
                "scheme_code":      code,
                "isin_growth":      isin_growth,
                "isin_div_reinvest": isin_div,
                "scheme_name":      name,
                "nav":              nav,
                "date":             nav_date,
                "fund_house":       current_fund_house,
                "category":         current_category,
                "source":           "AMFI",
            })

        logger.info("AMFI crawler parsed %d schemes", len(results))
        return results
