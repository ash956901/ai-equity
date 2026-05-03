"""Business logic for screening and saved screens."""

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models import Company, CompanyTheme, FinancialRatio, SavedScreen


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
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        min_market_cap: Optional[int] = None,
        max_market_cap: Optional[int] = None,
        themes: Optional[list[str]] = None,
        min_theme_confidence: Optional[float] = None,
        asymmetric_only: bool = False,
        min_pe: Optional[float] = None,
        max_pe: Optional[float] = None,
        min_roe: Optional[float] = None,
        max_debt_to_equity: Optional[float] = None,
        limit: int = 50,
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

        if themes:
            theme_q = (
                self.db.query(CompanyTheme.company_id)
                .filter(CompanyTheme.is_active.is_(True))
                .filter(CompanyTheme.theme_name.in_(themes))
            )
            if min_theme_confidence is not None:
                theme_q = theme_q.filter(
                    CompanyTheme.confidence_score >= Decimal(str(min_theme_confidence))
                )
            if asymmetric_only:
                theme_q = theme_q.filter(CompanyTheme.is_asymmetric.is_(True))
            query = query.filter(Company.id.in_(theme_q))

        if any(
            v is not None
            for v in (min_pe, max_pe, min_roe, max_debt_to_equity)
        ):
            ratio_q = self.db.query(FinancialRatio.company_id).distinct()
            if min_pe is not None:
                ratio_q = ratio_q.filter(FinancialRatio.pe_ratio >= Decimal(str(min_pe)))
            if max_pe is not None:
                ratio_q = ratio_q.filter(FinancialRatio.pe_ratio <= Decimal(str(max_pe)))
            if min_roe is not None:
                ratio_q = ratio_q.filter(FinancialRatio.roe >= Decimal(str(min_roe)))
            if max_debt_to_equity is not None:
                ratio_q = ratio_q.filter(
                    FinancialRatio.debt_to_equity <= Decimal(str(max_debt_to_equity))
                )
            query = query.filter(Company.id.in_(ratio_q))

        companies = (
            query.order_by(Company.market_cap_inr.desc().nullslast())
            .limit(limit)
            .all()
        )
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
