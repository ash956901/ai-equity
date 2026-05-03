"""Historical OHLCV candles for a ticker, with tiered provider fallback.

Order: Upstox (when access_token configured) -> yfinance (free, no key) -> FMP.
Caches each (ticker, range, interval) tuple in Redis with a TTL that scales
with the range so 1Y/5Y don't get rebuilt on every visit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.config import get_settings
from src.services.cache_service import CacheService, CacheTTL

logger = logging.getLogger(__name__)


# (range, default_interval, yf_period, yf_interval, lookback_days)
_RANGE_TABLE: dict[str, dict[str, Any]] = {
    "1D": {
        "default_interval": "5m",
        "yf_period": "1d",
        "yf_interval": "5m",
        "lookback_days": 1,
        "ttl": CacheTTL.CANDLES_INTRADAY,
    },
    "1W": {
        "default_interval": "30m",
        "yf_period": "5d",
        "yf_interval": "30m",
        "lookback_days": 7,
        "ttl": CacheTTL.CANDLES_SHORT,
    },
    "1M": {
        "default_interval": "1d",
        "yf_period": "1mo",
        "yf_interval": "1d",
        "lookback_days": 31,
        "ttl": CacheTTL.CANDLES_MEDIUM,
    },
    "6M": {
        "default_interval": "1d",
        "yf_period": "6mo",
        "yf_interval": "1d",
        "lookback_days": 183,
        "ttl": CacheTTL.CANDLES_MEDIUM,
    },
    "1Y": {
        "default_interval": "1d",
        "yf_period": "1y",
        "yf_interval": "1d",
        "lookback_days": 366,
        "ttl": CacheTTL.CANDLES_LONG,
    },
    "5Y": {
        "default_interval": "1wk",
        "yf_period": "5y",
        "yf_interval": "1wk",
        "lookback_days": 366 * 5,
        "ttl": CacheTTL.CANDLES_LONG,
    },
    "MAX": {
        "default_interval": "1mo",
        "yf_period": "max",
        "yf_interval": "1mo",
        "lookback_days": 366 * 25,
        "ttl": CacheTTL.CANDLES_LONG,
    },
}


@dataclass
class Candle:
    t: str  # ISO timestamp (UTC)
    o: float
    h: float
    l: float
    c: float
    v: Optional[float]


def _to_yf_symbol(ticker: str, exchange: str = "NSE") -> str:
    """yfinance Indian-equity symbol convention: 'RELIANCE.NS' / 'RELIANCE.BO'."""
    upper = ticker.upper().strip()
    if upper.endswith(".NS") or upper.endswith(".BO"):
        return upper
    suffix = ".NS" if exchange.upper() != "BSE" else ".BO"
    return f"{upper}{suffix}"


def _normalize_range(rng: str) -> str:
    rng = (rng or "1Y").upper()
    return rng if rng in _RANGE_TABLE else "1Y"


class HistoricalService:
    """Tiered OHLCV provider with Redis cache."""

    def __init__(self) -> None:
        self.cache = CacheService()
        self.settings = get_settings()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def get_candles(
        self,
        *,
        ticker: str,
        rng: str = "1Y",
        interval: Optional[str] = None,
        exchange: str = "NSE",
        isin: Optional[str] = None,
    ) -> dict[str, Any]:
        rng = _normalize_range(rng)
        cfg = _RANGE_TABLE[rng]
        interval = interval or cfg["default_interval"]

        cache_key = f"{ticker.upper()}:{exchange.upper()}:{rng}:{interval}"
        cached = self.cache.get("candles", cache_key)
        if cached:
            return cached

        candles, source = self._fetch_with_fallback(
            ticker=ticker, exchange=exchange, rng=rng, interval=interval, isin=isin
        )
        result = {
            "ticker": ticker.upper(),
            "exchange": exchange.upper(),
            "range": rng,
            "interval": interval,
            "source": source,
            "ohlcv": [c.__dict__ for c in candles],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        self.cache.set("candles", cache_key, result, ttl=cfg["ttl"])
        return result

    # ------------------------------------------------------------------
    #  Provider fallback chain
    # ------------------------------------------------------------------

    def _fetch_with_fallback(
        self,
        *,
        ticker: str,
        exchange: str,
        rng: str,
        interval: str,
        isin: Optional[str] = None,
    ) -> tuple[list[Candle], str]:
        # 1. yfinance (free, no key) — primary because broker keys are
        #    user-specific and we want guests to see charts too.
        try:
            candles = self._fetch_yfinance(
                ticker=ticker, exchange=exchange, rng=rng, interval=interval
            )
            if candles:
                return candles, "yfinance"
        except Exception as exc:
            logger.debug("yfinance candles failed: %s", exc)

        # 2. Upstox (when access token + ISIN are both available)
        try:
            candles = self._fetch_upstox(
                isin=isin, exchange=exchange, rng=rng, interval=interval
            )
            if candles:
                return candles, "upstox"
        except Exception as exc:
            logger.debug("upstox candles failed: %s", exc)

        # 3. FMP
        try:
            candles = self._fetch_fmp(
                ticker=ticker, exchange=exchange, rng=rng, interval=interval
            )
            if candles:
                return candles, "fmp"
        except Exception as exc:
            logger.debug("fmp candles failed: %s", exc)

        return [], "none"

    # ------------------------------------------------------------------
    #  yfinance
    # ------------------------------------------------------------------

    def _fetch_yfinance(
        self, *, ticker: str, exchange: str, rng: str, interval: str
    ) -> list[Candle]:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            return []
        cfg = _RANGE_TABLE[rng]
        symbol = _to_yf_symbol(ticker, exchange)
        df = yf.Ticker(symbol).history(
            period=cfg["yf_period"],
            interval=interval if interval in {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"} else cfg["yf_interval"],
            auto_adjust=False,
        )
        if df is None or df.empty:
            return []
        candles: list[Candle] = []
        for ts, row in df.iterrows():
            try:
                t = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                if not hasattr(t, "isoformat"):
                    continue
                candles.append(
                    Candle(
                        t=t.isoformat(),
                        o=float(row["Open"]),
                        h=float(row["High"]),
                        l=float(row["Low"]),
                        c=float(row["Close"]),
                        v=float(row["Volume"]) if "Volume" in row and row["Volume"] is not None else None,
                    )
                )
            except Exception:
                continue
        return candles

    # ------------------------------------------------------------------
    #  Upstox v2 historical-candle endpoint
    #  Requires both an access token (env: UPSTOX_ACCESS_TOKEN) and the
    #  company's ISIN (passed in by QuotesDomainService).
    # ------------------------------------------------------------------

    _UPSTOX_INTERVAL_MAP = {
        "1m": "1minute",
        "5m": "30minute",  # Upstox doesn't expose 5m; fall to 30m
        "15m": "30minute",
        "30m": "30minute",
        "1h": "30minute",
        "1d": "day",
        "1wk": "week",
        "1mo": "month",
    }

    def _fetch_upstox(
        self,
        *,
        isin: Optional[str],
        exchange: str,
        rng: str,
        interval: str,
    ) -> list[Candle]:
        if not self.settings.upstox_access_token or not isin:
            return []
        try:
            import httpx
        except ImportError:
            return []

        cfg = _RANGE_TABLE[rng]
        upstox_interval = self._UPSTOX_INTERVAL_MAP.get(interval, "day")
        instrument_key = (
            f"NSE_EQ|{isin}" if exchange.upper() == "NSE" else f"BSE_EQ|{isin}"
        )
        to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        from_date = (
            datetime.now(timezone.utc) - timedelta(days=int(cfg["lookback_days"]))
        ).strftime("%Y-%m-%d")
        url = (
            f"https://api.upstox.com/v2/historical-candle/"
            f"{instrument_key}/{upstox_interval}/{to_date}/{from_date}"
        )
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.upstox_access_token}",
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json() or {}
        except Exception as exc:
            logger.debug("upstox historical-candle error: %s", exc)
            return []

        rows = (data.get("data") or {}).get("candles") or []
        candles: list[Candle] = []
        # Upstox returns candles newest-first as
        # [timestamp, open, high, low, close, volume, oi].
        for row in reversed(rows):
            try:
                if len(row) < 6:
                    continue
                t_iso = str(row[0])
                candles.append(
                    Candle(
                        t=t_iso,
                        o=float(row[1]),
                        h=float(row[2]),
                        l=float(row[3]),
                        c=float(row[4]),
                        v=float(row[5]) if row[5] is not None else None,
                    )
                )
            except Exception:
                continue
        return candles

    # ------------------------------------------------------------------
    #  FMP (last resort, paid)
    # ------------------------------------------------------------------

    def _fetch_fmp(
        self, *, ticker: str, exchange: str, rng: str, interval: str
    ) -> list[Candle]:
        api_key = self.settings.fmp_api_key
        if not api_key:
            return []
        # FMP historical-price-full?serietype=line / historical-chart/{interval}/{symbol}
        # Indian symbols on FMP are like "RELIANCE.NS" too. We map yfinance-style.
        try:
            import httpx

            symbol = _to_yf_symbol(ticker, exchange)
            cfg = _RANGE_TABLE[rng]
            cutoff = datetime.utcnow() - timedelta(days=int(cfg["lookback_days"]))
            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
            params = {"apikey": api_key, "from": cutoff.date().isoformat()}
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json() or {}
            rows = data.get("historical") or []
            candles: list[Candle] = []
            for row in reversed(rows):
                try:
                    candles.append(
                        Candle(
                            t=row["date"],
                            o=float(row["open"]),
                            h=float(row["high"]),
                            l=float(row["low"]),
                            c=float(row["close"]),
                            v=float(row.get("volume") or 0) or None,
                        )
                    )
                except Exception:
                    continue
            return candles
        except Exception as exc:
            logger.debug("fmp candles error: %s", exc)
            return []
