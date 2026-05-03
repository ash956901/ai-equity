"""Ticker-keyed quote / candles / peers service.

Wraps the existing company-id-keyed ``QuotesService`` and the new
``HistoricalService`` so the frontend can address stocks by ticker
(``RELIANCE`` / ``INFY``) without first resolving to a UUID.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.db.models import Company, FinancialRatio
from src.services.market_data.context import MarketDataContext
from src.services.market_data.historical_service import HistoricalService

logger = logging.getLogger(__name__)


def _resolve_company(db: Session, ticker: str) -> Optional[Company]:
    upper = ticker.upper().strip()
    bare = upper.replace(".NS", "").replace(".BO", "")
    return (
        db.query(Company)
        .filter(
            or_(
                Company.ticker_nse == bare,
                Company.ticker_bse == bare,
                Company.ticker_nse == upper,
                Company.ticker_bse == upper,
            )
        )
        .first()
    )


class QuotesDomainService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._historical = HistoricalService()

    # ------------------------------------------------------------------
    #  Quote by ticker
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> dict[str, Any]:
        company = _resolve_company(self.db, ticker)
        result: dict[str, Any] = {
            "ticker": ticker.upper(),
            "name": None,
            "exchange": "NSE",
            "company_id": None,
        }
        if company is None:
            result["error"] = "Unknown ticker"
            return result
        result["company_id"] = str(company.id)
        result["name"] = company.name
        result["sector"] = company.sector
        result["industry"] = company.industry

        try:
            from src.services.market_data.quotes_service import QuotesService

            with MarketDataContext(self.db) as ctx:
                svc = QuotesService(ctx)
                payload = asyncio.run(svc.get_quote(company.id))
            if isinstance(payload, dict):
                result.update({k: v for k, v in payload.items() if k not in result or result[k] is None})
        except Exception as exc:
            logger.debug("quote enrichment failed for %s: %s", ticker, exc)
        return result

    # ------------------------------------------------------------------
    #  Candles
    # ------------------------------------------------------------------

    def get_candles(
        self, *, ticker: str, rng: str, interval: Optional[str]
    ) -> dict[str, Any]:
        company = _resolve_company(self.db, ticker)
        exchange = "NSE"
        symbol = ticker
        isin: Optional[str] = None
        if company:
            symbol = company.ticker_nse or company.ticker_bse or ticker
            if not company.ticker_nse and company.ticker_bse:
                exchange = "BSE"
            isin = company.isin
        result = self._historical.get_candles(
            ticker=symbol,
            rng=rng,
            interval=interval,
            exchange=exchange,
            isin=isin,
        )
        result["company_id"] = str(company.id) if company else None
        return result

    # ------------------------------------------------------------------
    #  Peers
    # ------------------------------------------------------------------

    def get_peers(self, ticker: str, *, limit: int = 8) -> list[dict[str, Any]]:
        company = _resolve_company(self.db, ticker)
        if company is None:
            return []
        q = (
            self.db.query(Company)
            .filter(Company.id != company.id)
            .filter(Company.listing_status == "active")
        )
        if company.industry:
            peers = (
                q.filter(Company.industry == company.industry)
                .order_by(Company.market_cap_inr.desc().nullslast())
                .limit(limit)
                .all()
            )
            if peers:
                return [self._serialize_peer(p) for p in peers]
        if company.sector:
            peers = (
                q.filter(Company.sector == company.sector)
                .order_by(Company.market_cap_inr.desc().nullslast())
                .limit(limit)
                .all()
            )
            return [self._serialize_peer(p) for p in peers]
        return []

    def _serialize_peer(self, p: Company) -> dict[str, Any]:
        latest_ratio = (
            self.db.query(FinancialRatio)
            .filter(FinancialRatio.company_id == p.id)
            .order_by(FinancialRatio.period_end.desc().nullslast())
            .first()
        )
        return {
            "company_id": str(p.id),
            "name": p.name,
            "ticker_nse": p.ticker_nse,
            "ticker_bse": p.ticker_bse,
            "sector": p.sector,
            "industry": p.industry,
            "market_cap_inr": p.market_cap_inr,
            "pe_ratio": float(latest_ratio.pe_ratio) if latest_ratio and latest_ratio.pe_ratio is not None else None,
            "roe": float(latest_ratio.roe) if latest_ratio and latest_ratio.roe is not None else None,
        }
