"""SEBI curation crawler — fixed implementation.

Root cause of 403:
  The SEBI curation page (sebi.gov.in/curation/) sits behind a WAF that blocks
  programmatic access with a hard 403 regardless of headers. This is by design —
  SEBI's curation pages are HTML directories that *link to* NSE and BSE, not data
  sources themselves. Scraping sebi.gov.in/curation/ gives you zero filing content.

Correct architecture:
  1. Parse the SEBI curation table ONCE (fetched via web_fetch / cached HTML) to
     extract the canonical NSE + BSE endpoint URLs for each filing category.
  2. Hit those NSE/BSE endpoints directly — they return actual filing data.
  3. Optionally keep the SEBI RSS feed as a signal layer for new circulars.

This module implements that corrected flow.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SEBI curation table — pre-parsed.
# These are the actual NSE/BSE endpoints the SEBI page links to.
# Re-run _parse_sebi_curation_page() if SEBI updates their table.
# ---------------------------------------------------------------------------

SEBI_FILING_CATEGORIES: List[Dict[str, str]] = [
    {
        "category": "Corporate Governance",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-governance",
        "bse_url": "https://www.bseindia.com/corporates/Corpgovernane.aspx",
    },
    {
        "category": "Shareholding Patterns",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
        "bse_url": "https://www.bseindia.com/corporates/Sharehold_Searchnew.aspx",
    },
    {
        "category": "Financial Results",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-financial-results",
        "bse_url": "https://www.bseindia.com/corporates/Comp_Resultsnew.aspx",
    },
    {
        "category": "Insider Trading Disclosure",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-insider-trading",
        "bse_url": "https://www.bseindia.com/corporates/xbrldetails.aspx",
    },
    {
        "category": "Voting Results",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-voting-results",
        "bse_url": "https://www.bseindia.com/corporates/VotingResult.aspx",
    },
    {
        "category": "Related Party Transactions",
        "nse_url": "https://www.nseindia.com/companies-listing/related-party-transactions",
        "bse_url": "https://www.bseindia.com/corporates.html",
    },
    {
        "category": "Secretarial Compliance",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-secretarial-compliance-report",
        "bse_url": "https://www.bseindia.com/corporates.html",
    },
    {
        "category": "Statement of Deviation/Variation",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-statement-of-deviation-variation",
        "bse_url": "https://www.bseindia.com/corporates/xbrldetails.aspx",
    },
    {
        "category": "Business Responsibility & Sustainability",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-bussiness-sustainabilitiy-reports",
        "bse_url": "https://www.bseindia.com/corporates.html",
    },
    {
        "category": "Investor Complaints",
        "nse_url": "https://www.nseindia.com/companies-listing/corporate-filings-investor-complaints",
        "bse_url": "https://www.bseindia.com/corporates.html",
    },
]

# NSE JSON API endpoints — these return structured data, much better than scraping
NSE_API_ENDPOINTS: Dict[str, str] = {
    "announcements":       "https://www.nseindia.com/api/corporate-announcements?index=equities",
    "announcements_sme":   "https://www.nseindia.com/api/corporate-announcements?index=sme",
    "board_meetings":      "https://www.nseindia.com/api/home-board-meetings",
    "financial_results":   "https://www.nseindia.com/api/corporates-financial-results?index=equities",
    "shareholding":        "https://www.nseindia.com/api/corporate-share-holdings-master?index=equities",
    "actions":             "https://www.nseindia.com/api/corporates-corporateActions?index=equities",
    # Filtered by symbol:
    "company_filings":     "https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}",
    "company_fin_results": "https://www.nseindia.com/api/corporates-financial-results?index=equities&symbol={symbol}",
}

# NSE headers — session priming is REQUIRED; NSE rejects cold API calls
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# BSE API endpoints
BSE_API_ENDPOINTS: Dict[str, str] = {
    "announcements":     "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&strCat=-1&strPrevDate={since_date}&strScrip=&strSearch=P&strToDate={to_date}&strType=C",
    "financial_results": "https://api.bseindia.com/BseIndiaAPI/api/getFinancialResultsData/w?scripcode={bse_code}&type=quartely",
    "shareholding":      "https://api.bseindia.com/BseIndiaAPI/api/SHoldingPatterns/w?Scripcode={bse_code}",
    "company_search":    "https://api.bseindia.com/BseIndiaAPI/api/fetchCompanySearch/w?search={symbol}",
}

BSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
}


# ---------------------------------------------------------------------------
# Session factories
# ---------------------------------------------------------------------------

def _make_session(headers: Dict[str, str], prime_url: Optional[str] = None) -> requests.Session:
    """Build a session with retry logic and optional cookie priming."""
    session = requests.Session()
    session.headers.update(headers)

    retry = Retry(
        total=3,
        backoff_factor=2,           # 2s, 4s, 8s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    if prime_url:
        try:
            # Fetch the main page first so NSE/BSE set their session cookies.
            # Without this step their API endpoints return 403.
            session.get(prime_url, timeout=15)
            time.sleep(1)           # brief pause after priming
        except Exception as exc:
            logger.warning("Session priming failed for %s: %s", prime_url, exc)

    return session


# ---------------------------------------------------------------------------
# Main crawler
# ---------------------------------------------------------------------------

class SEBICrawler:
    """
    Crawls corporate filing data from NSE and BSE — the actual sources that
    SEBI's curation page redirects to.

    Why not sebi.gov.in directly?
      SEBI's curation pages are a static HTML table of links pointing to NSE/BSE.
      The site returns 403 to all programmatic requests (WAF-enforced).
      Going straight to NSE/BSE APIs is correct and gives structured JSON data.
    """

    def __init__(self, prefer_source: str = "nse"):
        """
        Args:
            prefer_source: "nse" or "bse" — which exchange API to hit first.
                           Falls back to the other on failure.
        """
        self.prefer_source = prefer_source.lower()
        self._nse_session: Optional[requests.Session] = None
        self._bse_session: Optional[requests.Session] = None

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    @property
    def nse_session(self) -> requests.Session:
        if self._nse_session is None:
            self._nse_session = _make_session(
                NSE_HEADERS,
                prime_url="https://www.nseindia.com",
            )
        return self._nse_session

    @property
    def bse_session(self) -> requests.Session:
        if self._bse_session is None:
            self._bse_session = _make_session(
                BSE_HEADERS,
                prime_url="https://www.bseindia.com",
            )
        return self._bse_session

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def crawl(
        self,
        company_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        bse_code: Optional[str] = None,
        since_date: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch corporate filings from NSE/BSE.

        Args:
            company_id: Internal company UUID (stored in returned records).
            symbol: NSE ticker symbol e.g. "RELIANCE".
            bse_code: BSE 6-digit scrip code e.g. "500325". Needed for BSE-only endpoints.
            since_date: ISO date string "YYYY-MM-DD" — filters results from this date.
            categories: Subset of SEBI_FILING_CATEGORIES["category"] to fetch.
                        None means fetch all: announcements + financial results.

        Returns:
            List of filing metadata dicts, each containing:
                company_id, symbol, category, filing_type,
                date, subject, attachment_url, source.
        """
        results: List[Dict[str, Any]] = []

        # General announcements (no symbol filter)
        if symbol:
            results += self._fetch_nse_company_filings(symbol, since_date, company_id)
            results += self._fetch_nse_financial_results(symbol, since_date, company_id)
        else:
            results += self._fetch_nse_announcements(since_date, company_id)

        # BSE announcements (complements NSE — some filings appear on one only)
        results += self._fetch_bse_announcements(since_date, bse_code, company_id)

        logger.info(
            "SEBICrawler: fetched %d total filings (symbol=%s, since=%s)",
            len(results), symbol, since_date,
        )
        return results

    def get_filing_categories(self) -> List[Dict[str, str]]:
        """Return the SEBI curation category map (pre-parsed, no HTTP needed)."""
        return SEBI_FILING_CATEGORIES

    # ------------------------------------------------------------------
    # NSE fetchers
    # ------------------------------------------------------------------

    def _fetch_nse_announcements(
        self,
        since_date: Optional[str],
        company_id: Optional[UUID],
    ) -> List[Dict[str, Any]]:
        url = NSE_API_ENDPOINTS["announcements"]
        return self._get_nse_json(url, "announcement", since_date, company_id)

    def _fetch_nse_company_filings(
        self,
        symbol: str,
        since_date: Optional[str],
        company_id: Optional[UUID],
    ) -> List[Dict[str, Any]]:
        url = NSE_API_ENDPOINTS["company_filings"].format(symbol=symbol)
        return self._get_nse_json(url, "announcement", since_date, company_id, symbol=symbol)

    def _fetch_nse_financial_results(
        self,
        symbol: str,
        since_date: Optional[str],
        company_id: Optional[UUID],
    ) -> List[Dict[str, Any]]:
        url = NSE_API_ENDPOINTS["company_fin_results"].format(symbol=symbol)
        return self._get_nse_json(url, "financial_result", since_date, company_id, symbol=symbol)

    def _get_nse_json(
        self,
        url: str,
        filing_type: str,
        since_date: Optional[str],
        company_id: Optional[UUID],
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            resp = self.nse_session.get(url, timeout=15)
            resp.raise_for_status()
            raw = resp.json()
        except requests.HTTPError as exc:
            logger.error("NSE API error %s for %s", exc.response.status_code, url)
            return []
        except Exception as exc:
            logger.error("NSE fetch failed (%s): %s", url, exc)
            return []

        # NSE wraps data differently per endpoint — normalise both shapes
        items = raw if isinstance(raw, list) else raw.get("data", raw.get("resultData", []))

        results = []
        for item in items:
            date_val = (
                item.get("exchdisstime")        # announcements
                or item.get("broadcastDate")
                or item.get("xbrlAttachement", {}).get("attachmentDate", "")
                or ""
            )
            # Date filter
            if since_date and date_val and date_val[:10] < since_date:
                continue

            attachment = (
                item.get("attchmntFile")
                or item.get("filingXbrl")
                or ""
            )
            if attachment and not attachment.startswith("http"):
                attachment = f"https://www.nseindia.com{attachment}"

            results.append({
                "company_id":     str(company_id) if company_id else None,
                "symbol":         symbol or item.get("symbol", ""),
                "category":       item.get("subject", ""),
                "filing_type":    filing_type,
                "date":           date_val,
                "subject":        item.get("desc", item.get("subject", "")),
                "attachment_url": attachment,
                "source":         "NSE",
                "raw":            item,          # keep raw for downstream parsing
            })

        return results

    # ------------------------------------------------------------------
    # BSE fetchers
    # ------------------------------------------------------------------

    def _fetch_bse_announcements(
        self,
        since_date: Optional[str],
        bse_code: Optional[str],
        company_id: Optional[UUID],
    ) -> List[Dict[str, Any]]:
        from datetime import date
        to_date = date.today().strftime("%Y%m%d")
        from_date = since_date.replace("-", "") if since_date else "20240101"

        url = BSE_API_ENDPOINTS["announcements"].format(
            since_date=from_date,
            to_date=to_date,
        )
        if bse_code:
            url = url.replace("strScrip=", f"strScrip={bse_code}")

        try:
            resp = self.bse_session.get(url, timeout=15)
            resp.raise_for_status()
            raw = resp.json()
        except requests.HTTPError as exc:
            logger.error("BSE API error %s for %s", exc.response.status_code, url)
            return []
        except Exception as exc:
            logger.error("BSE fetch failed (%s): %s", url, exc)
            return []

        items = raw.get("Table", [])
        results = []
        for item in items:
            date_val = item.get("DissemDT", "")
            attachment = item.get("ATTACHMENTNAME", "")
            if attachment:
                attachment = f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{attachment}"

            results.append({
                "company_id":     str(company_id) if company_id else None,
                "symbol":         item.get("SCRIP_CD", bse_code or ""),
                "category":       item.get("CATEGORYNAME", ""),
                "filing_type":    "announcement",
                "date":           date_val,
                "subject":        item.get("HEADLINE", ""),
                "attachment_url": attachment,
                "source":         "BSE",
                "raw":            item,
            })

        return results


# ---------------------------------------------------------------------------
# Utility: re-parse the SEBI curation page if their table changes
# ---------------------------------------------------------------------------

def _parse_sebi_curation_page(html: str) -> List[Dict[str, str]]:
    """
    Parse the SEBI corporate_filings.html table into a list of category dicts.
    Pass in the raw HTML string (fetched once, cached).

    Returns list of {"category": ..., "nse_url": ..., "bse_url": ...}
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    categories = []
    for row in table.find_all("tr")[1:]:          # skip header row
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        category_text = cols[1].get_text(" ", strip=True).split("NSE")[0].strip()
        nse_link = cols[2].find("a")
        bse_link = cols[3].find("a")

        categories.append({
            "category": category_text,
            "nse_url":  nse_link["href"] if nse_link else "",
            "bse_url":  bse_link["href"] if bse_link else "",
        })

    return categories