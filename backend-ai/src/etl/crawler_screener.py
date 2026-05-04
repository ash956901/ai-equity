"""Screener.in crawler.

Fetches 10-year financials, ratios, shareholding patterns, quarterly results,
annual report links, concall transcripts, and credit ratings.

HTML structure (confirmed from live scrape of screener.in/company/RELIANCE/consolidated/):
  - All financial tables live in <section> tags with stable IDs:
      #profit-loss        → annual P&L (10 years + TTM)
      #balance-sheet      → annual balance sheet
      #cash-flow          → annual cash flow
      #ratios             → efficiency ratios (ROCE, debtor days, etc.)
      #shareholding       → promoter / FII / DII quarterly pattern
      #quarters           → last ~12 quarters of results
  - Each section has a <table> with:
      <thead> row of period headers  (e.g. "Mar 2024", "Mar 2025", "TTM")
      <tbody> rows where first <td> is the metric name, rest are values
  - Company metadata (price, market cap, PE, etc.) lives in
      #top > .company-ratios  as <li> elements
  - Documents (annual reports, concalls, credit ratings, announcements)
    live in  #documents  as grouped <div class="documents"> blocks
  - Analysis (pros/cons) lives in #analysis > ul.pros / ul.cons

Notes:
  - screener.in does NOT require login for consolidated/standalone pages.
  - Session priming (GET /) is needed to receive cookies before the company page.
  - Requests rate-limit at ~20 req/min without triggering blocks; stay under.
  - The page is server-rendered HTML — no JS execution needed.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_URL = "https://www.screener.in"
COMPANY_URL = BASE_URL + "/company/{symbol}/{view}/"  # view: "" | "consolidated"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.screener.in/",
}

# Stable section IDs on screener.in company pages
SECTION_IDS = [
    "quarters",
    "profit-loss",
    "balance-sheet",
    "cash-flow",
    "ratios",
    "shareholding",
]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

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

    # Prime session — screener.in sets CSRF cookies on the home page
    try:
        session.get(BASE_URL + "/", timeout=15)
        time.sleep(0.5)
    except Exception as exc:
        logger.warning("Session priming failed: %s", exc)

    return session


# ---------------------------------------------------------------------------
# Table parser
# ---------------------------------------------------------------------------

def _parse_financial_table(section: Tag) -> Dict[str, Any]:
    """
    Parse a screener.in financial table section into:
      { "headers": [...], "data": { "Metric": { "Mar 2024": val, ... } } }

    Table layout:
      <thead><tr><th></th><th>Mar 2024</th>...</tr></thead>
      <tbody>
        <tr><td>Sales</td><td>500</td>...</tr>
        ...
      </tbody>
    """
    table = section.find("table")
    if not table:
        return {"headers": [], "data": {}}

    # Headers — skip the first empty <th> (row-label column)
    header_row = table.find("thead")
    headers: List[str] = []
    if header_row:
        headers = [
            th.get_text(strip=True)
            for th in header_row.find_all("th")[1:]
        ]

    data: Dict[str, Dict[str, Any]] = {}
    tbody = table.find("tbody")
    if not tbody:
        return {"headers": headers, "data": data}

    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        metric = cells[0].get_text(strip=True)
        if not metric:
            continue

        values = {}
        for i, cell in enumerate(cells[1:]):
            if i >= len(headers):
                break
            raw = cell.get_text(strip=True).replace(",", "")
            # Try to coerce to number; keep as string if it looks like a % or label
            if raw.endswith("%"):
                values[headers[i]] = raw          # keep "12%" as string
            else:
                try:
                    values[headers[i]] = float(raw) if "." in raw else int(raw)
                except ValueError:
                    values[headers[i]] = raw       # e.g. empty or dash

        data[metric] = values

    return {"headers": headers, "data": data}


# ---------------------------------------------------------------------------
# Metadata parser
# ---------------------------------------------------------------------------

def _parse_company_meta(soup: BeautifulSoup) -> Dict[str, str]:
    """Parse the top-bar company ratios (price, market cap, PE, etc.)"""
    meta: Dict[str, str] = {}

    # Company name
    name_tag = soup.select_one("h1.margin-0")
    if name_tag:
        meta["company_name"] = name_tag.get_text(strip=True)

    # Ratio list items:  <li><span class="name">Market Cap</span> <span class="value">...</span></li>
    for li in soup.select("#top .company-ratios li, .company-ratios li"):
        name_span = li.find("span", class_="name")
        value_span = li.find("span", class_="value") or li.find("span", class_="number")
        if name_span and value_span:
            key = name_span.get_text(strip=True).rstrip(":")
            val = value_span.get_text(strip=True)
            meta[key] = val

    return meta


# ---------------------------------------------------------------------------
# Analysis (pros / cons) parser
# ---------------------------------------------------------------------------

def _parse_analysis(soup: BeautifulSoup) -> Dict[str, List[str]]:
    section = soup.find("section", id="analysis")
    if not section:
        return {"pros": [], "cons": []}

    pros = [li.get_text(strip=True) for li in section.select("ul.pros li")]
    cons = [li.get_text(strip=True) for li in section.select("ul.cons li")]
    return {"pros": pros, "cons": cons}


# ---------------------------------------------------------------------------
# CAGRs parser
# ---------------------------------------------------------------------------

def _parse_cagrs(soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
    """
    Screener shows CAGR tables inside #profit-loss section as small inline tables
    or inside a separate div — selectors vary but the text is consistent.
    """
    cagrs: Dict[str, Dict[str, str]] = {}

    # They live in <div class="ranges"> or similar inside each section
    for div in soup.select(".ranges, .cagrs"):
        rows = div.find_all("li") or div.find_all("tr")
        current_label = div.find_previous("h2")
        label = current_label.get_text(strip=True) if current_label else "CAGR"
        cagrs.setdefault(label, {})
        for row in rows:
            text = row.get_text(" ", strip=True)
            # Pattern: "10 Years: 12%"
            match = re.search(r"([\d]+\s+Years?|TTM|Last Year)[:\s]+([\-\d\.]+%?)", text)
            if match:
                cagrs[label][match.group(1)] = match.group(2)

    return cagrs


# ---------------------------------------------------------------------------
# Documents parser
# ---------------------------------------------------------------------------

def _parse_documents(soup: BeautifulSoup) -> Dict[str, List[Dict[str, str]]]:
    """
    Parse the #documents section:
      - Annual reports   → { year, link }
      - Concalls         → { month, transcript?, ppt?, recording? }
      - Credit ratings   → { title, date, source, link }
      - Announcements    → { title, description, link }
    """
    docs: Dict[str, List[Dict[str, str]]] = {
        "annual_reports": [],
        "concalls": [],
        "credit_ratings": [],
        "announcements": [],
    }

    section = soup.find("section", id="documents")
    if not section:
        return docs

    # Annual reports
    for li in section.select(".annual-reports li, [data-type='annual-reports'] li"):
        a = li.find("a", href=True)
        if a:
            docs["annual_reports"].append({
                "year": li.get_text(" ", strip=True).replace(a.get_text(strip=True), "").strip(),
                "link": a["href"],
            })

    # Concalls — group links by month label
    for li in section.select(".concalls li, [data-type='concalls'] li"):
        month_text = li.get_text(" ", strip=True)
        entry: Dict[str, str] = {}
        month_match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}", month_text)
        if month_match:
            entry["month"] = month_match.group(0)
        for a in li.find_all("a", href=True):
            link_text = a.get_text(strip=True).lower()
            href = a["href"]
            if "transcript" in link_text:
                entry["transcript"] = href
            elif "ppt" in link_text or "presentation" in link_text:
                entry["ppt"] = href
            elif "recording" in link_text or "audio" in link_text or "youtube" in href:
                entry["recording"] = href
            else:
                entry.setdefault("link", href)
        if entry:
            docs["concalls"].append(entry)

    # Credit ratings
    for li in section.select(".credit-ratings li, [data-type='credit-ratings'] li"):
        a = li.find("a", href=True)
        if a:
            docs["credit_ratings"].append({
                "title": a.get_text(strip=True),
                "link": a["href"],
                "raw_text": li.get_text(" ", strip=True),
            })

    # Announcements
    for li in section.select(".announcements li, [data-type='announcements'] li"):
        a = li.find("a", href=True)
        if a:
            docs["announcements"].append({
                "title": a.get_text(strip=True),
                "link": a["href"] if a["href"].startswith("http") else BASE_URL + a["href"],
                "description": li.get_text(" ", strip=True),
            })

    return docs


# ---------------------------------------------------------------------------
# Main crawler
# ---------------------------------------------------------------------------

class ScreenerCrawler:
    """
    Crawls screener.in for a given NSE/BSE symbol and returns structured
    financial data ready for your ETL pipeline.

    Usage:
        crawler = ScreenerCrawler()
        data = crawler.crawl(symbol="RELIANCE", consolidated=True)

    Returns a dict with keys:
        meta, analysis, quarters, profit_loss, balance_sheet,
        cash_flow, ratios, shareholding, documents, cagrs
    """

    def __init__(self, delay_between_requests: float = 3.0):
        """
        Args:
            delay_between_requests: Seconds to wait between company fetches.
                                    screener.in rate-limits at ~20 req/min;
                                    3s keeps you well under that.
        """
        self.delay = delay_between_requests
        self._session: Optional[requests.Session] = None
        self._last_request_time: float = 0.0

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = _build_session()
        return self._session

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def crawl(
        self,
        symbol: str,
        consolidated: bool = True,
        company_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Fetch all financial data for a symbol from screener.in.

        Args:
            symbol:       NSE ticker (e.g. "RELIANCE") or BSE code (e.g. "500325").
            consolidated: If True, fetch consolidated financials; else standalone.
            company_id:   Optional internal UUID stored in returned record.

        Returns:
            {
              "symbol": str,
              "company_id": str | None,
              "source": "screener.in",
              "url": str,
              "meta": { market_cap, pe, pb, ... },
              "analysis": { "pros": [...], "cons": [...] },
              "quarters": { "headers": [...], "data": { metric: { period: value } } },
              "profit_loss": { ... same shape ... },
              "balance_sheet": { ... },
              "cash_flow": { ... },
              "ratios": { ... },
              "shareholding": { ... },
              "documents": {
                  "annual_reports": [...],
                  "concalls": [...],
                  "credit_ratings": [...],
                  "announcements": [...],
              },
              "cagrs": { ... },
            }
        """
        view = "consolidated" if consolidated else ""
        url = COMPANY_URL.format(symbol=symbol.upper(), view=view)

        soup = self._fetch(url)
        if soup is None:
            return self._empty_result(symbol, company_id, url)

        result: Dict[str, Any] = {
            "symbol":     symbol.upper(),
            "company_id": str(company_id) if company_id else None,
            "source":     "screener.in",
            "url":        url,
            "meta":       _parse_company_meta(soup),
            "analysis":   _parse_analysis(soup),
            "cagrs":      _parse_cagrs(soup),
            "documents":  _parse_documents(soup),
        }

        # Financial tables
        section_map = {
            "quarters":      "quarters",
            "profit-loss":   "profit_loss",
            "balance-sheet": "balance_sheet",
            "cash-flow":     "cash_flow",
            "ratios":        "ratios",
            "shareholding":  "shareholding",
        }
        for section_id, result_key in section_map.items():
            section = soup.find("section", id=section_id)
            if section:
                result[result_key] = _parse_financial_table(section)
            else:
                logger.debug("Section #%s not found for %s", section_id, symbol)
                result[result_key] = {"headers": [], "data": {}}

        logger.info(
            "screener.in crawled %s (%s) — %d P&L rows, %d quarter cols",
            symbol,
            "consolidated" if consolidated else "standalone",
            len(result["profit_loss"]["data"]),
            len(result["quarters"].get("headers", [])),
        )
        return result

    def crawl_many(
        self,
        symbols: List[str],
        consolidated: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Crawl multiple symbols with rate-limit delay between each.

        Args:
            symbols:      List of NSE tickers.
            consolidated: Fetch consolidated view for all.

        Returns:
            List of crawl result dicts (failures are logged and skipped).
        """
        results = []
        for symbol in symbols:
            result = self.crawl(symbol, consolidated=consolidated)
            if result["profit_loss"]["data"]:   # non-empty = success
                results.append(result)
            else:
                logger.warning("Empty result for %s — skipping", symbol)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL with rate limiting and return BeautifulSoup or None."""
        # Enforce delay between requests
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        try:
            resp = self.session.get(url, timeout=20)
            self._last_request_time = time.monotonic()

            if resp.status_code == 404:
                logger.warning("Symbol not found on screener.in: %s", url)
                return None
            if resp.status_code == 403:
                logger.error(
                    "screener.in returned 403 for %s. "
                    "Session may be blocked — recreating session.", url
                )
                self._session = None   # force session rebuild on next call
                return None
            if resp.status_code != 200:
                logger.warning("screener.in returned %d for %s", resp.status_code, url)
                return None

            return BeautifulSoup(resp.text, "html.parser")

        except requests.Timeout:
            logger.error("Timeout fetching %s", url)
            return None
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            return None

    @staticmethod
    def _empty_result(
        symbol: str,
        company_id: Optional[UUID],
        url: str,
    ) -> Dict[str, Any]:
        return {
            "symbol":       symbol.upper(),
            "company_id":   str(company_id) if company_id else None,
            "source":       "screener.in",
            "url":          url,
            "meta":         {},
            "analysis":     {"pros": [], "cons": []},
            "quarters":     {"headers": [], "data": {}},
            "profit_loss":  {"headers": [], "data": {}},
            "balance_sheet":{"headers": [], "data": {}},
            "cash_flow":    {"headers": [], "data": {}},
            "ratios":       {"headers": [], "data": {}},
            "shareholding": {"headers": [], "data": {}},
            "documents":    {
                "annual_reports": [],
                "concalls":       [],
                "credit_ratings": [],
                "announcements":  [],
            },
            "cagrs":        {},
        }
