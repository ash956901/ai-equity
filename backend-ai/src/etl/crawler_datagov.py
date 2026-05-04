"""data.gov.in MCA company master crawler.

Source: https://data.gov.in — Ministry of Corporate Affairs open data.

The MCA company master dataset contains CIN, company name, registration status,
activity code, authorized capital, paid-up capital, state, and date of registration
for all Indian companies.

data.gov.in has two public endpoints:
  1. /resource/{id}  — requires API key (free registration at data.gov.in)
  2. /lists          — free, returns dataset metadata + limited record previews

This crawler supports both:
  - With API key:  hits /resource/{id} for full paginated access (up to 10k/call)
  - Without key:   uses /lists to discover and list available MCA datasets
"""

import csv
import io
import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# data.gov.in API bases
DATA_GOV_RESOURCE_API = "https://api.data.gov.in/resource"
DATA_GOV_LISTS_API = "https://api.data.gov.in/lists"

# Known resource IDs for MCA datasets (state-wise, updated periodically)
# Use discover_datasets() to find current ones
MCA_RESOURCE_IDS: Dict[str, str] = {
    "Karnataka":  "080e668f-1e57-4376-8269-b41ca9c39cc6",
    "Maharashtra": "6176ee09-3c27-4734-acab-8e77ecb7e4f3",
    "Nagaland":   "6a6e802c-66e2-47c2-ad20-4abc9289c85b",
    "Mizoram":    "87f853c6-59ee-41dd-aaa2-2fbdfb660ced",
}

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


class DataGovCrawler:
    """Crawler for data.gov.in MCA Company Master data.

    Usage:
        # Discover available MCA datasets (no key needed)
        crawler = DataGovCrawler()
        datasets = crawler.discover_datasets()

        # Fetch records with API key
        crawler = DataGovCrawler(api_key="your-key")
        data = crawler.crawl(resource_id="080e668f-...", limit=500)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: data.gov.in API key. Get one free at https://data.gov.in.
                     Required for /resource/ endpoint. Not needed for discover_datasets().
        """
        self.api_key = api_key
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = _build_session()
        return self._session

    # ------------------------------------------------------------------
    # Discovery (no API key needed)
    # ------------------------------------------------------------------

    def discover_datasets(
        self,
        search: str = "company master",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Discover available MCA datasets on data.gov.in (no API key needed).

        Args:
            search: Search term to filter dataset titles.
            limit:  Max datasets to return.

        Returns:
            List of dataset metadata dicts with keys:
                title, index_name (resource_id), org, source, created, updated
        """
        params: Dict[str, Any] = {
            "format": "json",
            "limit": limit,
            "filters[title]": search,
        }

        try:
            resp = self.session.get(DATA_GOV_LISTS_API, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            records = data.get("records", [])
            total = data.get("total", 0)

            results = []
            for rec in records:
                results.append({
                    "title":       rec.get("title", ""),
                    "resource_id": rec.get("index_name", ""),
                    "org":         rec.get("org", []),
                    "source":      rec.get("source", ""),
                    "created":     rec.get("created", ""),
                    "updated":     rec.get("updated", ""),
                    "desc":        rec.get("desc", ""),
                })

            logger.info(
                "data.gov.in: discovered %d / %d MCA datasets for '%s'",
                len(results), total, search,
            )
            return results

        except Exception as exc:
            logger.error("data.gov.in discovery failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Fetch records (API key required)
    # ------------------------------------------------------------------

    def crawl(
        self,
        resource_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        state: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch MCA company master records from data.gov.in.

        Requires an API key. Get one free at https://data.gov.in.

        Args:
            resource_id: data.gov.in resource ID. If None, uses Karnataka dataset.
            limit:       Number of records to fetch (max 10000 per call).
            offset:      Pagination offset.
            state:       Filter by Indian state.
            status:      Filter by company status (e.g. "Active").

        Returns:
            List of company dicts.
        """
        if not self.api_key:
            logger.warning(
                "data.gov.in /resource/ endpoint requires an API key. "
                "Register free at https://data.gov.in to get one. "
                "Using discover_datasets() instead (no key needed)."
            )
            return self.discover_datasets()

        rid = resource_id or MCA_RESOURCE_IDS.get("Karnataka", list(MCA_RESOURCE_IDS.values())[0])

        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": min(limit, 10000),
            "offset": offset,
        }

        # Optional filters
        if state:
            params["filters[state]"] = state
        if status:
            params["filters[company_status]"] = status

        url = f"{DATA_GOV_RESOURCE_API}/{rid}"

        try:
            resp = self.session.get(url, params=params, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                records = data.get("records", [])
                total = data.get("total", 0)

                results = []
                for rec in records:
                    results.append({
                        "cin":                   rec.get("cin", rec.get("CIN", "")),
                        "company_name":          rec.get("company_name", rec.get("COMPANY_NAME", "")),
                        "status":                rec.get("company_status", rec.get("STATUS", "")),
                        "activity_code":         rec.get("activity_code", rec.get("ACTIVITY_CODE", "")),
                        "activity_description":  rec.get("activity_description", rec.get("ACTIVITY_DESC", "")),
                        "authorized_capital":    rec.get("authorized_capital", rec.get("AUTHORIZED_CAPITAL", "")),
                        "paid_up_capital":       rec.get("paidup_capital", rec.get("PAID_UP_CAPITAL", "")),
                        "state":                 rec.get("state", rec.get("STATE", "")),
                        "date_of_registration":  rec.get("date_of_registration", rec.get("DATE_OF_REGISTRATION", "")),
                        "company_class":         rec.get("company_class", rec.get("COMPANY_CLASS", "")),
                        "company_category":      rec.get("company_category", rec.get("COMPANY_CATEGORY", "")),
                        "email":                 rec.get("email", ""),
                        "source":                "data.gov.in",
                    })

                logger.info(
                    "data.gov.in: fetched %d / %d MCA records (offset=%d)",
                    len(results), total, offset,
                )
                return results
            else:
                logger.warning("data.gov.in returned %d: %s", resp.status_code, resp.text[:200])
                return []

        except Exception as exc:
            logger.error("data.gov.in fetch failed: %s", exc)
            return []

    def crawl_all(
        self,
        resource_id: Optional[str] = None,
        batch_size: int = 1000,
        max_records: int = 5000,
        state: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Paginate through the full MCA dataset (requires API key).

        Args:
            resource_id: data.gov.in resource ID.
            batch_size:  Records per API call.
            max_records: Stop after this many total records.
            state:       Optional state filter.
            status:      Optional status filter.

        Returns:
            Aggregated list of company dicts.
        """
        all_records: List[Dict[str, Any]] = []
        offset = 0

        while len(all_records) < max_records:
            batch = self.crawl(
                resource_id=resource_id,
                limit=batch_size,
                offset=offset,
                state=state,
                status=status,
            )
            if not batch:
                break
            all_records.extend(batch)
            offset += batch_size
            time.sleep(0.5)

        logger.info("data.gov.in: total fetched %d MCA records", len(all_records))
        return all_records[:max_records]
