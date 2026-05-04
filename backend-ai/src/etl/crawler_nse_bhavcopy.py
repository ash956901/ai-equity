"""NSE Bhavcopy crawler.

Fetches daily OHLCV + delivery data from NSE archives.
Source: https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv

CSV columns:
  SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE,
  LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS,
  NO_OF_TRADES, DELIV_QTY, DELIV_PER

Notes:
  - File is available after market close (~6:30 PM IST).
  - Weekends and market holidays return 404.
  - This crawler auto-scans backwards to find the latest available date.
"""

import csv
import io
import logging
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BHAVCOPY_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class NSEBhavcopycrawler:
    """Crawler for NSE daily bhavcopy (OHLCV + delivery).

    Usage:
        crawler = NSEBhavcopycrawler()

        # Fetch latest available bhavcopy
        data = crawler.crawl()

        # Fetch for a specific date
        data = crawler.crawl(target_date=date(2026, 4, 30))

        # Fetch for a symbol
        data = crawler.crawl(symbol="RELIANCE")
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
        target_date: Optional[date] = None,
        symbol: Optional[str] = None,
        series: str = "EQ",
    ) -> List[Dict[str, Any]]:
        """Fetch bhavcopy data.

        Args:
            target_date: Specific date. None = auto-find latest available.
            symbol:      Filter to a single NSE symbol (e.g. "RELIANCE").
            series:      Filter by series (default "EQ" for equity).
                         Pass None to get all series.

        Returns:
            List of dicts with keys:
                symbol, series, date, prev_close, open, high, low,
                last, close, avg_price, volume, turnover_lacs,
                trades, delivery_qty, delivery_pct, source
        """
        if target_date is None:
            csv_text, actual_date = self._find_latest()
        else:
            csv_text = self._fetch_date(target_date)
            actual_date = target_date

        if csv_text is None:
            logger.warning("No bhavcopy data found")
            return []

        records = self._parse_csv(csv_text, symbol, series)
        for rec in records:
            rec["date"] = actual_date.isoformat() if actual_date else ""

        logger.info(
            "NSE bhavcopy: %d records for %s (symbol=%s, series=%s)",
            len(records), actual_date, symbol, series,
        )
        return records

    def _find_latest(self, lookback_days: int = 7) -> tuple:
        """Scan backwards from today to find the latest available bhavcopy."""
        today = date.today()
        for delta in range(lookback_days):
            d = today - timedelta(days=delta)
            csv_text = self._fetch_date(d)
            if csv_text:
                return csv_text, d
        return None, None

    def _fetch_date(self, d: date) -> Optional[str]:
        """Fetch bhavcopy CSV for a specific date."""
        url = BHAVCOPY_URL.format(date=d.strftime("%d%m%Y"))
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200 and len(resp.text) > 100:
                return resp.text
            return None
        except Exception as exc:
            logger.debug("Bhavcopy fetch failed for %s: %s", d, exc)
            return None

    def _parse_csv(
        self,
        csv_text: str,
        symbol_filter: Optional[str],
        series_filter: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Parse the bhavcopy CSV text into structured records."""
        reader = csv.DictReader(io.StringIO(csv_text))

        results: List[Dict[str, Any]] = []
        for row in reader:
            # Normalize keys (CSV has trailing spaces in headers)
            row = {k.strip(): v.strip() if v else "" for k, v in row.items()}

            sym = row.get("SYMBOL", "")
            ser = row.get("SERIES", "")

            # Apply filters
            if symbol_filter and sym.upper() != symbol_filter.upper():
                continue
            if series_filter and ser != series_filter:
                continue

            try:
                results.append({
                    "symbol":        sym,
                    "series":        ser,
                    "prev_close":    self._to_float(row.get("PREV_CLOSE")),
                    "open":          self._to_float(row.get("OPEN_PRICE")),
                    "high":          self._to_float(row.get("HIGH_PRICE")),
                    "low":           self._to_float(row.get("LOW_PRICE")),
                    "last":          self._to_float(row.get("LAST_PRICE")),
                    "close":         self._to_float(row.get("CLOSE_PRICE")),
                    "avg_price":     self._to_float(row.get("AVG_PRICE")),
                    "volume":        self._to_int(row.get("TTL_TRD_QNTY")),
                    "turnover_lacs": self._to_float(row.get("TURNOVER_LACS")),
                    "trades":        self._to_int(row.get("NO_OF_TRADES")),
                    "delivery_qty":  self._to_int(row.get("DELIV_QTY")),
                    "delivery_pct":  self._to_float(row.get("DELIV_PER")),
                    "source":        "NSE_Bhavcopy",
                })
            except Exception as exc:
                logger.debug("Skipping row %s: %s", sym, exc)

        return results

    @staticmethod
    def _to_float(val: Optional[str]) -> Optional[float]:
        if val is None or val.strip() == "" or val.strip() == "-":
            return None
        try:
            return float(val.replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _to_int(val: Optional[str]) -> Optional[int]:
        if val is None or val.strip() == "" or val.strip() == "-":
            return None
        try:
            return int(val.replace(",", ""))
        except ValueError:
            return None
