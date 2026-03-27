"""Financial data service — now delegates to RealTimeDataService for live fallback."""

from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.services.realtime_data import RealTimeDataService


class FinancialService:
    """Service for financial data access and ratio calculation.

    Wraps :class:`RealTimeDataService` so that callers (agents, routes)
    get the DB → API → scrape fallback chain transparently.
    """

    def __init__(self, db: Session):
        self.db = db
        self._rt = RealTimeDataService(db)

    def get_latest_financials(
        self, company_id: UUID, periods: int = 4
    ) -> Dict[str, Any]:
        """Get latest financial statements with real-time fallback."""
        return self._rt.get_financials(company_id, periods)

    def calculate_ratios(
        self, company_id: UUID, period: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get or compute financial ratios with scrape fallback."""
        return self._rt.get_ratios(company_id, period)
