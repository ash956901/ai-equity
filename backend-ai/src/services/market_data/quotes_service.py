"""Quote retrieval service with API->scrape fallback chain."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import httpx

from src.db.models import Company
from src.services.cache_service import CacheTTL
from src.services.market_data.context import MarketDataContext

logger = logging.getLogger(__name__)


class QuotesService:
    """Fetches and caches latest company quotes."""

    def __init__(self, context: MarketDataContext):
        self.context = context

    async def get_quote(self, company_id: UUID) -> dict[str, Any]:
        company = (
            self.context.db.query(Company).filter(Company.id == company_id).first()
        )
        if not company:
            return {"error": "Company not found"}

        cache_key = str(company_id)
        cached = self.context.cache.get("quote", cache_key)
        if cached:
            return cached

        result = await self._fetch_quote_from_api(company)
        if not result:
            result = self._fetch_quote_from_scraper(company)
        if not result:
            result = {
                "company_id": str(company_id),
                "name": company.name,
                "quote": None,
                "message": "No live data available",
            }

        result["company_id"] = str(company_id)
        result["name"] = company.name
        self.context.cache.set("quote", cache_key, result, CacheTTL.QUOTE_LTP)
        return result

    async def _fetch_quote_from_api(self, company: Company) -> Optional[dict[str, Any]]:
        if company.isin:
            try:
                from src.integrations.market_data.upstox import UpstoxClient

                client = UpstoxClient()
                if client.access_token:
                    nse_key = f"NSE_EQ|{company.isin}"
                    data = await client.get_ltp_quote([nse_key])
                    if data and data.get("data"):
                        quote_data = (
                            list(data["data"].values())[0]
                            if isinstance(data["data"], dict)
                            else data["data"]
                        )
                        return {
                            "source": "Upstox",
                            "last_price": quote_data.get(
                                "last_price", quote_data.get("ltp")
                            ),
                            "instrument_key": nse_key,
                            "fetched_at": datetime.utcnow().isoformat(),
                        }
            except Exception as e:
                logger.debug("Upstox quote failed for %s: %s", company.isin, e)

        kite_ticker = company.ticker_nse or company.ticker_bse
        if kite_ticker:
            try:
                from src.integrations.market_data.kite import KiteClient

                client = KiteClient()
                exchange = "NSE" if company.ticker_nse else "BSE"
                instruments = [f"{exchange}:{kite_ticker}"]
                data = await client.get_ltp(instruments)
                if data:
                    quote_data = (
                        list(data.values())[0] if isinstance(data, dict) else data
                    )
                    return {
                        "source": "Kite",
                        "last_price": quote_data.get(
                            "last_price", quote_data.get("ltp")
                        ),
                        "fetched_at": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                logger.debug("Kite quote failed for %s: %s", kite_ticker, e)

        alpha_quote = await self._fetch_quote_from_alpha_vantage(company)
        if alpha_quote:
            return alpha_quote

        return None

    async def _fetch_quote_from_alpha_vantage(
        self, company: Company
    ) -> Optional[dict[str, Any]]:
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
        if not api_key:
            return None

        symbols: list[str] = []
        if company.ticker_nse:
            symbols.extend([f"{company.ticker_nse}.NSE", company.ticker_nse])
        if company.ticker_bse:
            symbols.extend([f"{company.ticker_bse}.BSE", company.ticker_bse])

        seen: set[str] = set()
        unique_symbols = [s for s in symbols if not (s in seen or seen.add(s))]

        for symbol in unique_symbols:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        "https://www.alphavantage.co/query",
                        params={
                            "function": "GLOBAL_QUOTE",
                            "symbol": symbol,
                            "apikey": api_key,
                        },
                    )
                    response.raise_for_status()

                payload = response.json()
                quote = payload.get("Global Quote", {}) if isinstance(payload, dict) else {}
                price_raw = quote.get("05. price")
                if not price_raw:
                    continue

                last_price = float(price_raw)
                change = float(quote["09. change"]) if quote.get("09. change") else None
                change_pct_raw = quote.get("10. change percent")
                change_pct = (
                    float(change_pct_raw.replace("%", "")) if change_pct_raw else None
                )
                volume = int(quote["06. volume"]) if quote.get("06. volume") else None

                return {
                    "source": "AlphaVantage",
                    "symbol": quote.get("01. symbol") or symbol,
                    "last_price": last_price,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": volume,
                    "previous_close": (
                        float(quote["08. previous close"]) if quote.get("08. previous close") else None
                    ),
                    "fetched_at": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                logger.debug("Alpha Vantage quote failed for %s: %s", symbol, e)

        return None

    def _fetch_quote_from_scraper(self, company: Company) -> Optional[dict[str, Any]]:
        data = self.context.scraper.get_company_overview(
            ticker_nse=company.ticker_nse,
            ticker_bse=company.ticker_bse,
            isin=company.isin,
        )
        if data and data.get("last_price"):
            return {
                "source": data.get("source", "web"),
                "last_price": data["last_price"],
                "change": data.get("change"),
                "change_pct": data.get("change_pct"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "volume": data.get("volume"),
                "fetched_at": data.get("fetched_at", datetime.utcnow().isoformat()),
            }
        return None
