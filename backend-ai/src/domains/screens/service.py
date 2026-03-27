"""Business logic for screening and saved screens."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models import Company, SavedScreen


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
