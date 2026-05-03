"""Business logic for screening and saved screens."""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models import Company, SavedScreen, CompanyTheme
from src.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class ScreensService:
    """Handles saved screen CRUD and screen execution."""

    def __init__(self, db: Session):
        self.db = db

    def list_screens(self, user_id: UUID) -> list[dict[str, Any]]:
        screens = (
            self.db.query(SavedScreen)
            .filter(SavedScreen.user_id == user_id)
            .order_by(SavedScreen.created_at.desc())
            .all()
        )
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "filters": s.filters or {},
                "created_at": s.created_at.isoformat(),
            }
            for s in screens
        ]

    def save_screen(self, user_id: UUID, name: str, filters: dict[str, Any]) -> dict[str, Any]:
        screen = SavedScreen(
            user_id=user_id,
            name=name,
            filters=filters,
        )
        self.db.add(screen)
        self.db.commit()
        self.db.refresh(screen)
        return {"id": str(screen.id), "name": screen.name}

    def run_screen(
        self,
        sector: Optional[str],
        industry: Optional[str],
        min_market_cap: Optional[int],
        max_market_cap: Optional[int],
        limit: int,
    ) -> list[dict[str, Any]]:
        query = self.db.query(Company).filter(Company.listing_status == "active")

        if sector:
            query = query.filter(Company.sector == sector)
        if industry:
            query = query.filter(Company.industry == industry)
        if min_market_cap:
            query = query.filter(Company.market_cap_inr >= min_market_cap)
        if max_market_cap:
            query = query.filter(Company.market_cap_inr <= max_market_cap)

        companies = query.order_by(Company.market_cap_inr.desc().nullslast()).limit(limit).all()
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "ticker_nse": c.ticker_nse,
                "ticker_bse": c.ticker_bse,
                "sector": c.sector,
                "industry": c.industry,
                "market_cap_inr": c.market_cap_inr,
            }
            for c in companies
        ]

    def thematic_search(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        """Semantic AI theme-based discovery across all company filings.

        Uses VectorService.thematic_search to find companies whose filing
        disclosures semantically match the investment theme, then enriches
        each result with company metadata from PostgreSQL.
        """
        try:
            vector_svc = VectorService()
            raw_results = vector_svc.thematic_search(query=query, limit=limit * 3)
        except Exception as exc:
            logger.error("Thematic vector search failed: %s", exc)
            raw_results = []
            
        enriched: list[dict[str, Any]] = []
        seen_company_ids: set[str] = set()

        # SQL Fallback
        sql_themes = self.db.query(CompanyTheme).filter(CompanyTheme.theme_name.ilike(f"%{query}%")).all()
        for theme in sql_themes:
            if str(theme.company_id) not in seen_company_ids:
                company = self.db.query(Company).filter(Company.id == theme.company_id).first()
                if company:
                    seen_company_ids.add(str(company.id))
                    enriched.append({
                        "company_id": str(company.id),
                        "company_name": company.name,
                        "ticker_nse": company.ticker_nse,
                        "ticker_bse": company.ticker_bse,
                        "sector": company.sector,
                        "industry": company.industry,
                        "market_cap_inr": company.market_cap_inr,
                        "relevance_score": float(theme.confidence_score),
                        "match_count": 1,
                        "evidence_snippets": [f"Direct exposure to {theme.theme_name}"],
                    })

        for result in raw_results:
            company_id_str = result.get("company_id")
            if not company_id_str or company_id_str in seen_company_ids:
                continue
            seen_company_ids.add(company_id_str)

            # Enrich with DB metadata
            try:
                company = (
                    self.db.query(Company)
                    .filter(Company.id == company_id_str)
                    .first()
                )
            except Exception:
                company = None

            enriched.append(
                {
                    "company_id": company_id_str,
                    "company_name": result.get("company_name") or (company.name if company else "Unknown"),
                    "ticker_nse": company.ticker_nse if company else None,
                    "ticker_bse": company.ticker_bse if company else None,
                    "sector": company.sector if company else None,
                    "industry": company.industry if company else None,
                    "market_cap_inr": company.market_cap_inr if company else None,
                    "relevance_score": round(result.get("max_score", 0), 4),
                    "match_count": result.get("match_count", 1),
                    "evidence_snippets": result.get("evidence", []),
                }
            )

            if len(enriched) >= limit:
                break

        # Sort by relevance descending
        enriched.sort(key=lambda x: x["relevance_score"], reverse=True)
        return enriched
