"""Company API routes — real-time data with full NSE/BSE universe support."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Company
from src.services.financial_service import FinancialService
from src.services.realtime_data import RealTimeDataService
from src.utils.data_sources import company_sources, financial_sources, quote_sources

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/")
def list_companies(
    limit: int = 50,
    offset: int = 0,
    sector: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List companies with optional sector filter and search.

    Returns paginated results from the full NSE+BSE universe.
    """
    q = db.query(Company).filter(Company.listing_status == "active")
    if sector:
        q = q.filter(Company.sector == sector)
    if search:
        s = f"%{search}%"
        q = q.filter(
            Company.name.ilike(s)
            | Company.ticker_nse.ilike(s)
            | Company.ticker_bse.ilike(s)
            | Company.isin.ilike(s)
        )

    total = q.count()
    companies = q.order_by(Company.name).offset(offset).limit(limit).all()

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


@router.get("/search")
def search_companies(
    q: str = Query(..., min_length=1, description="Search by name, ticker, or ISIN"),
    limit: int = 20,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Fast company search across the full universe."""
    svc = RealTimeDataService(db)
    return svc.find_company(q, limit)


@router.get("/stats")
def universe_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get statistics about the loaded stock universe."""
    from src.services.stock_universe import StockUniverseService

    svc = StockUniverseService(db)
    return svc.get_universe_stats()


@router.get("/{company_id}")
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
) -> Dict[str, Any]:
    """Get company details. Triggers background enrichment if data is sparse."""
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    if background_tasks and not c.sector:
        from src.etl.tasks import enrich_single_company
        background_tasks.add_task(enrich_single_company.delay, str(company_id))

    return {
        "id": str(c.id),
        "name": c.name,
        "legal_name": c.legal_name,
        "ticker_nse": c.ticker_nse,
        "ticker_bse": c.ticker_bse,
        "isin": c.isin,
        "sector": c.sector,
        "industry": c.industry,
        "sub_industry": c.sub_industry,
        "market_cap_inr": c.market_cap_inr,
        "website_domain": c.website_domain,
        "ir_page_url": c.ir_page_url,
        "description": c.description,
        "listing_status": c.listing_status,
        "data_sources": company_sources(c.ticker_nse, c.ticker_bse),
    }


@router.get("/{company_id}/quote")
async def get_company_quote(
    company_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get real-time stock quote (Upstox → Kite → FMP → web scrape)."""
    svc = RealTimeDataService(db)
    result = await svc.get_quote(company_id)
    company = db.query(Company).filter(Company.id == company_id).first()
    ticker = company.ticker_nse if company else None
    result["data_sources"] = quote_sources(result.get("source", ""), ticker)
    return result


@router.get("/{company_id}/financials")
def get_company_financials(
    company_id: UUID,
    periods: int = 4,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get latest financials with real-time fallback."""
    svc = FinancialService(db)
    result = svc.get_latest_financials(company_id, periods)
    company = db.query(Company).filter(Company.id == company_id).first()
    ticker = company.ticker_nse if company else None
    result["data_sources"] = financial_sources(ticker, result.get("source"))
    return result


@router.get("/{company_id}/ratios")
def get_company_ratios(
    company_id: UUID,
    period: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get financial ratios with web-scrape fallback."""
    from datetime import date

    svc = FinancialService(db)
    p = date.fromisoformat(period) if period else None
    result = svc.calculate_ratios(company_id, p)
    company = db.query(Company).filter(Company.id == company_id).first()
    ticker = company.ticker_nse if company else None
    result["data_sources"] = financial_sources(ticker, result.get("source"))
    return result


@router.post("/{company_id}/enrich")
def enrich_company(
    company_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger enrichment of a company from web sources."""
    svc = RealTimeDataService(db)
    return svc.enrich_company(company_id)


@router.post("/{company_id}/refresh")
def refresh_company(company_id: UUID) -> Dict[str, Any]:
    """Trigger full background refresh: enrich + financials + filings."""
    from src.etl.tasks import refresh_company as refresh_task

    refresh_task.delay(str(company_id))
    return {"company_id": str(company_id), "status": "refresh_queued"}
