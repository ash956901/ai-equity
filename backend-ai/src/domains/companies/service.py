"""Business logic for company domain endpoints."""

from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from src.db.models import Company, CompanyComparisonSnapshot
from src.services.gemini_enrichment_service import GeminiEnrichmentService
from src.services.market_data.context import MarketDataContext
from src.services.market_data.enrichment_service import (
    CompanyEnrichmentService,
    CompanySearchService,
)
from src.services.market_data.quotes_service import QuotesService
from src.services.stock_universe import StockUniverseService
from src.services.financial_service import FinancialService
from src.utils.data_sources import company_sources, financial_sources, quote_sources


class CompaniesService:
    """Encapsulates company listing, details, enrichment, and analytics data."""

    COMPANY_CACHE_TTL_HOURS = 1
    PROFILE_CACHE_SOURCE = "company_profile_v1"
    QUOTE_CACHE_SOURCE = "company_quote_v1"
    FINANCIALS_CACHE_SOURCE_PREFIX = "company_fin_v1"
    RATIOS_CACHE_SOURCE_PREFIX = "company_rat_v1"

    def __init__(self, db: Session):
        self.db = db
        self._market_data_context = MarketDataContext(db)
        self._quotes = QuotesService(self._market_data_context)
        self._enrichment = CompanyEnrichmentService(self._market_data_context)
        self._search = CompanySearchService(self._market_data_context)
        self._financial = FinancialService(db)
        self._gemini = GeminiEnrichmentService()

    def get_universe_stats(self) -> dict[str, Any]:
        """Return stock-universe sync statistics."""
        svc = StockUniverseService(self.db)
        return svc.get_universe_stats()

    def list_companies(
        self,
        limit: int,
        offset: int,
        sector: Optional[str],
        search: Optional[str],
    ) -> dict[str, Any]:
        query = self.db.query(Company).filter(Company.listing_status == "active")
        if sector:
            query = query.filter(Company.sector == sector)
        if search:
            search_like = f"%{search}%"
            query = query.filter(
                Company.name.ilike(search_like)
                | Company.ticker_nse.ilike(search_like)
                | Company.ticker_bse.ilike(search_like)
                | Company.isin.ilike(search_like)
            )

        total = query.count()
        companies = query.order_by(Company.name).offset(offset).limit(limit).all()
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "companies": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "ticker_nse": c.ticker_nse,
                    "ticker_bse": c.ticker_bse,
                    "isin": c.isin,
                    "sector": c.sector,
                    "industry": c.industry,
                    "market_cap_inr": c.market_cap_inr,
                }
                for c in companies
            ],
        }

    def search_companies(self, query: str, limit: int) -> list[dict[str, Any]]:
        return self._search.find_company(query, limit)

    async def get_company(self, company_id: UUID, background_tasks: BackgroundTasks) -> dict[str, Any]:
        cached_profile = self._get_cache_snapshot(company_id, self.PROFILE_CACHE_SOURCE)
        if cached_profile:
            return cached_profile

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not company.sector:
            from src.etl.tasks import enrich_single_company

            task_obj: Any = enrich_single_company
            background_tasks.add_task(lambda cid=str(company_id): task_obj.delay(cid))

        known_fields = {
            "sector": company.sector,
            "industry": company.industry,
            "sub_industry": company.sub_industry,
            "description": company.description,
            "market_cap_inr": company.market_cap_inr,
            "website_domain": company.website_domain,
            "ir_page_url": company.ir_page_url,
        }
        gemini_extra = await self._gemini.get_company_extra_info(
            company_name=company.name,
            ticker_nse=company.ticker_nse,
            ticker_bse=company.ticker_bse,
            known_fields=known_fields,
        )

        payload = {
            "id": str(company.id),
            "name": company.name,
            "legal_name": company.legal_name,
            "ticker_nse": company.ticker_nse,
            "ticker_bse": company.ticker_bse,
            "isin": company.isin,
            "sector": company.sector,
            "industry": company.industry,
            "sub_industry": company.sub_industry,
            "market_cap_inr": company.market_cap_inr,
            "website_domain": company.website_domain,
            "ir_page_url": company.ir_page_url,
            "description": company.description,
            "listing_status": company.listing_status,
            "gemini_extra": gemini_extra,
            "data_sources": company_sources(company.ticker_nse, company.ticker_bse),
        }
        self._save_cache_snapshot(company_id, self.PROFILE_CACHE_SOURCE, payload)
        return payload

    async def get_quote(self, company_id: UUID) -> dict[str, Any]:
        cached_quote = self._get_cache_snapshot(company_id, self.QUOTE_CACHE_SOURCE)
        # Discard cached failures (no last_price) so the next request tries the live APIs again
        if cached_quote and cached_quote.get("last_price"):
            return cached_quote

        result = await self._quotes.get_quote(company_id)
        company = self.db.query(Company).filter(Company.id == company_id).first()
        ticker = company.ticker_nse if company else None
        result["data_sources"] = quote_sources(result.get("source", ""), ticker)
        # Only persist a snapshot when we actually got a price
        if result.get("last_price"):
            self._save_cache_snapshot(company_id, self.QUOTE_CACHE_SOURCE, result)
        return result

    def get_financials(self, company_id: UUID, periods: int) -> dict[str, Any]:
        cache_source = f"{self.FINANCIALS_CACHE_SOURCE_PREFIX}_{periods}"
        cached_financials = self._get_cache_snapshot(company_id, cache_source)
        if cached_financials:
            return cached_financials

        result = self._financial.get_latest_financials(company_id, periods)
        company = self.db.query(Company).filter(Company.id == company_id).first()
        ticker = company.ticker_nse if company else None
        result["data_sources"] = financial_sources(ticker, result.get("source"))
        self._save_cache_snapshot(company_id, cache_source, result)
        return result

    def get_ratios(self, company_id: UUID, period: Optional[str]) -> dict[str, Any]:
        period_key = period or "latest"
        cache_source = f"{self.RATIOS_CACHE_SOURCE_PREFIX}_{period_key}"
        cached_ratios = self._get_cache_snapshot(company_id, cache_source)
        if cached_ratios:
            return cached_ratios

        parsed_period = date.fromisoformat(period) if period else None
        result = self._financial.calculate_ratios(company_id, parsed_period)
        company = self.db.query(Company).filter(Company.id == company_id).first()
        ticker = company.ticker_nse if company else None
        result["data_sources"] = financial_sources(ticker, result.get("source"))
        self._save_cache_snapshot(company_id, cache_source, result)
        return result

    def get_filings(
        self, company_id: UUID, limit: int, filing_type: Optional[str]
    ) -> list[dict[str, Any]]:
        from src.db.models import Filing

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        query = self.db.query(Filing).filter(Filing.company_id == company_id)
        if filing_type:
            query = query.filter(Filing.filing_type == filing_type)
        filings = query.order_by(Filing.filing_date.desc()).limit(limit).all()
        return [
            {
                "id": str(f.id),
                "filing_type": f.filing_type,
                "title": f.title,
                "filing_date": f.filing_date.isoformat() if f.filing_date else None,
                "source_url": f.source_url,
                "status": f.status,
                "period_start": f.period_start.isoformat() if f.period_start else None,
                "period_end": f.period_end.isoformat() if f.period_end else None,
            }
            for f in filings
        ]

    def trigger_filings_sync(self, company_id: UUID) -> dict[str, Any]:
        from src.etl.tasks import crawl_bse_filings, crawl_nse_filings, crawl_ir_pages

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        cid = str(company_id)
        task_bse: Any = crawl_bse_filings
        task_nse: Any = crawl_nse_filings
        task_ir: Any = crawl_ir_pages
        task_bse.delay(company_id=cid)
        task_nse.delay(company_id=cid)
        task_ir.delay(company_id=cid)
        return {
            "status": "queued",
            "company_id": cid,
            "company_name": company.name,
            "sources": ["BSE", "NSE", "IR"],
        }

    def enrich_company(self, company_id: UUID) -> dict[str, Any]:
        return self._enrichment.enrich_company(company_id)

    def refresh_company(self, company_id: UUID) -> dict[str, Any]:
        from src.etl.tasks import refresh_company as refresh_task

        task_obj: Any = refresh_task
        task_obj.delay(str(company_id))
        return {"company_id": str(company_id), "status": "refresh_queued"}

    def _get_cache_snapshot(self, company_id: UUID, source: str) -> Optional[dict[str, Any]]:
        """Read non-expired cache payload from Postgres snapshots table."""
        now = datetime.utcnow()
        try:
            self.db.query(CompanyComparisonSnapshot).filter(
                CompanyComparisonSnapshot.company_id == company_id,
                CompanyComparisonSnapshot.source == source,
                CompanyComparisonSnapshot.expires_at <= now,
            ).delete(synchronize_session=False)
            self.db.commit()
        except Exception:
            self.db.rollback()

        row = (
            self.db.query(CompanyComparisonSnapshot)
            .filter(
                CompanyComparisonSnapshot.company_id == company_id,
                CompanyComparisonSnapshot.source == source,
                CompanyComparisonSnapshot.expires_at > now,
            )
            .order_by(CompanyComparisonSnapshot.fetched_at.desc())
            .first()
        )
        if not row:
            return None
        return row.payload if isinstance(row.payload, dict) else None

    def _save_cache_snapshot(self, company_id: UUID, source: str, payload: dict[str, Any]) -> None:
        """Persist cache payload with 1-hour TTL for repeat company requests."""
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.COMPANY_CACHE_TTL_HOURS)
        try:
            self.db.query(CompanyComparisonSnapshot).filter(
                CompanyComparisonSnapshot.company_id == company_id,
                CompanyComparisonSnapshot.source == source,
            ).delete(synchronize_session=False)

            snapshot = CompanyComparisonSnapshot(
                company_id=company_id,
                payload=payload,
                source=source,
                fetched_at=now,
                expires_at=expires_at,
            )
            self.db.add(snapshot)
            self.db.commit()
        except Exception:
            self.db.rollback()

    async def get_historical_prices(self, company_id: UUID, days: int = 30) -> dict[str, Any]:
        """Return daily OHLCV price history from Alpha Vantage."""
        import os
        import httpx

        cache_source = f"hist_prices_{days}"
        cached = self._get_cache_snapshot(company_id, cache_source)
        if cached:
            return cached

        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
        if not api_key:
            return {
                "company_id": str(company_id),
                "prices": [],
                "error": "Alpha Vantage API key not configured",
            }

        # Build candidate symbols — Alpha Vantage works with name-based symbols
        # Try ticker_nse with BSE suffix first (e.g., RELIANCE.BSE), then NSE suffix
        symbols: list[str] = []
        if company.ticker_nse:
            symbols.append(f"{company.ticker_nse}.BSE")  # e.g., RELIANCE.BSE
            symbols.append(f"{company.ticker_nse}.NSE")  # e.g., RELIANCE.NSE
        if company.ticker_bse and company.ticker_nse != company.ticker_bse:
            symbols.append(f"{company.ticker_bse}.BSE")  # numeric BSE code fallback

        outputsize = "full" if days > 100 else "compact"

        for symbol in symbols:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        "https://www.alphavantage.co/query",
                        params={
                            "function": "TIME_SERIES_DAILY",
                            "symbol": symbol,
                            "outputsize": outputsize,
                            "apikey": api_key,
                        },
                    )
                    response.raise_for_status()

                data = response.json()
                ts = data.get("Time Series (Daily)", {})
                if not ts:
                    continue

                # Parse and sort by date, take latest N days
                prices = []
                for dt_str, values in sorted(ts.items(), reverse=True)[:days]:
                    prices.append({
                        "date": dt_str,
                        "open": float(values.get("1. open", 0)),
                        "high": float(values.get("2. high", 0)),
                        "low": float(values.get("3. low", 0)),
                        "close": float(values.get("4. close", 0)),
                        "volume": int(values.get("5. volume", 0)),
                    })

                # Reverse so oldest first for charting
                prices.reverse()

                payload = {
                    "company_id": str(company_id),
                    "company_name": company.name,
                    "symbol": symbol,
                    "source": "AlphaVantage",
                    "days_requested": days,
                    "prices": prices,
                    "data_sources": [
                        {
                            "name": "Alpha Vantage",
                            "url": f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}",
                            "data_type": "historical_prices",
                        }
                    ],
                }
                self._save_cache_snapshot(company_id, cache_source, payload)
                return payload

            except Exception:
                continue

        return {
            "company_id": str(company_id),
            "company_name": company.name,
            "prices": [],
            "error": "Could not fetch historical prices from any source",
        }
