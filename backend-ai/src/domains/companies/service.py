"""Business logic for company domain endpoints."""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from src.db.models import Company
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

    def __init__(self, db: Session):
        self.db = db
        self._market_data_context = MarketDataContext(db)
        self._quotes = QuotesService(self._market_data_context)
        self._enrichment = CompanyEnrichmentService(self._market_data_context)
        self._search = CompanySearchService(self._market_data_context)
        self._financial = FinancialService(db)

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

    def get_company(self, company_id: UUID, background_tasks: BackgroundTasks) -> dict[str, Any]:
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not company.sector:
            from src.etl.tasks import enrich_single_company

            task_obj: Any = enrich_single_company
            background_tasks.add_task(lambda cid=str(company_id): task_obj.delay(cid))

        return {
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
            "data_sources": company_sources(company.ticker_nse, company.ticker_bse),
        }

    async def get_quote(self, company_id: UUID) -> dict[str, Any]:
        result = await self._quotes.get_quote(company_id)
        company = self.db.query(Company).filter(Company.id == company_id).first()
        ticker = company.ticker_nse if company else None
        result["data_sources"] = quote_sources(result.get("source", ""), ticker)
        return result

    def get_financials(self, company_id: UUID, periods: int) -> dict[str, Any]:
        result = self._financial.get_latest_financials(company_id, periods)
        company = self.db.query(Company).filter(Company.id == company_id).first()
        ticker = company.ticker_nse if company else None
        result["data_sources"] = financial_sources(ticker, result.get("source"))
        return result

    def get_ratios(self, company_id: UUID, period: Optional[str]) -> dict[str, Any]:
        parsed_period = date.fromisoformat(period) if period else None
        result = self._financial.calculate_ratios(company_id, parsed_period)
        company = self.db.query(Company).filter(Company.id == company_id).first()
        ticker = company.ticker_nse if company else None
        result["data_sources"] = financial_sources(ticker, result.get("source"))
        return result

    def enrich_company(self, company_id: UUID) -> dict[str, Any]:
        return self._enrichment.enrich_company(company_id)

    def refresh_company(self, company_id: UUID) -> dict[str, Any]:
        from src.etl.tasks import refresh_company as refresh_task

        task_obj: Any = refresh_task
        task_obj.delay(str(company_id))
        return {"company_id": str(company_id), "status": "refresh_queued"}
