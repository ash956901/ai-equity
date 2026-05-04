"""RBI macro data crawler.

Fetches key macroeconomic indicators from RBI's public pages:
  - Policy rates (Repo, Reverse Repo, CRR, SLR, MSF, Bank Rate)
  - Weekly Statistical Supplement highlights
  - Key monetary/banking aggregates

RBI does NOT provide a clean public REST API. DBIE (dbie.rbi.org.in) has SSL
issues and requires registration. Instead, this crawler scrapes the public
"Current Rates" and "Weekly Statistical Supplement" HTML pages, which are
stable and well-structured.

Sources:
  - https://www.rbi.org.in/scripts/BS_NSDPDisplay.aspx  (current policy rates)
  - https://www.rbi.org.in/scripts/WSSViewDetail.aspx    (weekly stats)
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

RBI_CURRENT_RATES_URL = "https://www.rbi.org.in/scripts/BS_NSDPDisplay.aspx"
RBI_WSS_URL = "https://www.rbi.org.in/scripts/WSSViewDetail.aspx?TYPE=Section&PARAM1=2"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
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


class RBICrawler:
    """Crawler for RBI macroeconomic data — policy rates and key indicators.

    Usage:
        crawler = RBICrawler()
        data = crawler.crawl()
        # data = { "policy_rates": {...}, "key_indicators": [...] }
    """

    def __init__(self):
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = _build_session()
        return self._session

    def crawl(self) -> Dict[str, Any]:
        """Fetch all available RBI macro data.

        Returns:
            {
              "policy_rates": { "Repo Rate": "6.50%", ... },
              "key_rates_table": [ { "indicator": ..., "rate": ..., "effective_from": ... }, ... ],
              "source": "RBI",
            }
        """
        result: Dict[str, Any] = {
            "policy_rates": {},
            "key_rates_table": [],
            "source": "RBI",
        }

        # Fetch policy rates
        rates = self._fetch_current_rates()
        result["policy_rates"] = rates.get("summary", {})
        result["key_rates_table"] = rates.get("table", [])

        logger.info(
            "RBI crawler: %d policy rates, %d table rows",
            len(result["policy_rates"]),
            len(result["key_rates_table"]),
        )
        return result

    def _fetch_current_rates(self) -> Dict[str, Any]:
        """Parse the RBI NSDP (National Summary Data Page).

        The page has a main table (table[1]) with 6 columns:
          [Indicator, Unit, Period, Latest Data, Previous Data, % Change]

        Data rows have non-empty first cell; blank rows and section headers
        are interspersed.
        """
        try:
            resp = self.session.get(RBI_CURRENT_RATES_URL, timeout=20)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("RBI current rates fetch failed: %s", exc)
            return {"summary": {}, "table": []}

        soup = BeautifulSoup(resp.text, "html.parser")

        summary: Dict[str, str] = {}
        table_data: List[Dict[str, str]] = []

        tables = soup.find_all("table")
        if len(tables) < 2:
            logger.warning("RBI: expected ≥2 tables, got %d", len(tables))
            return {"summary": summary, "table": table_data}

        # Main data table is the second one
        main_table = tables[1]
        current_section = ""

        for row in main_table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            texts = [c.get_text(" ", strip=True) for c in cells]

            # Skip empty rows
            if not any(texts):
                continue

            # Single-cell row → section header
            if len(cells) == 1 and texts[0]:
                current_section = texts[0]
                continue

            # Skip column-number rows ("1", "2", "3"...) and header rows
            if len(cells) >= 4 and texts[0] in ("1", "SDDS Data Category and Component"):
                continue

            # Data row: need at least 4 cells and a numeric value in col[3]
            if len(cells) >= 4:
                indicator = texts[0]
                unit = texts[1] if len(texts) > 1 else ""
                period = texts[2] if len(texts) > 2 else ""
                latest = texts[3] if len(texts) > 3 else ""
                previous = texts[4] if len(texts) > 4 else ""
                pct_change = texts[5] if len(texts) > 5 else ""

                if not indicator or not latest:
                    continue

                # Check if latest looks like a number
                if not re.search(r"[\d]", latest):
                    continue

                table_data.append({
                    "section":    current_section,
                    "indicator":  indicator,
                    "unit":       unit,
                    "period":     period,
                    "latest":     latest,
                    "previous":   previous,
                    "pct_change": pct_change,
                })

                # Build summary for key indicators
                summary[indicator] = latest

        return {"summary": summary, "table": table_data}

    def get_policy_rates(self) -> Dict[str, str]:
        """Convenience: return just the policy rates dict."""
        data = self.crawl()
        return data["policy_rates"]
