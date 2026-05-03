"""Build the personalised home payload in one round-trip.

Combines: user's watchlist companies, holdings, top asymmetric discovery
feed, recent timeline events, and suggested companies (sectors of
interest if set, otherwise large-caps). Cached per-user for 60 seconds.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.db.models import (
    Company,
    CompanyTheme,
    Filing,
    Holding,
    Portfolio,
    User,
    WatchlistCompany,
    WatchlistModel,
)
from src.services.cache_service import CacheService, CacheTTL

logger = logging.getLogger(__name__)


def _company_summary(c: Company) -> dict[str, Any]:
    return {
        "company_id": str(c.id),
        "name": c.name,
        "ticker_nse": c.ticker_nse,
        "ticker_bse": c.ticker_bse,
        "sector": c.sector,
        "industry": c.industry,
        "market_cap_inr": c.market_cap_inr,
    }


class HomeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.cache = CacheService()

    def get_personalized(self, user: User) -> dict[str, Any]:
        cache_key = str(user.id)
        cached = self.cache.get("home_personalized", cache_key)
        if cached:
            return cached

        payload = {
            "user": {
                "id": str(user.id),
                "username": user.username,
                "expertise_level": user.expertise_level,
                "default_chart_range": getattr(user, "default_chart_range", None),
            },
            "watchlist_companies": self._watchlist_companies(user.id),
            "holdings_companies": self._holdings_companies(user.id),
            "asymmetric_feed": self._asymmetric_feed(),
            "timeline_recent": self._timeline_recent(),
            "suggestions": self._suggestions(user),
            "generated_at": datetime.utcnow().isoformat(),
        }
        self.cache.set("home_personalized", cache_key, payload, CacheTTL.HOME_PERSONALIZED)
        return payload

    # --------------------------------------------------------------- #

    def _watchlist_companies(self, user_id: UUID) -> list[dict[str, Any]]:
        rows = (
            self.db.query(Company)
            .join(WatchlistCompany, WatchlistCompany.company_id == Company.id)
            .join(WatchlistModel, WatchlistModel.id == WatchlistCompany.watchlist_id)
            .filter(WatchlistModel.user_id == user_id)
            .order_by(WatchlistCompany.added_at.desc())
            .limit(20)
            .all()
        )
        return [_company_summary(c) for c in rows]

    def _holdings_companies(self, user_id: UUID) -> list[dict[str, Any]]:
        rows = (
            self.db.query(Company, Holding)
            .join(Holding, Holding.company_id == Company.id)
            .join(Portfolio, Portfolio.id == Holding.portfolio_id)
            .filter(Portfolio.user_id == user_id)
            .order_by(Holding.quantity.desc())
            .limit(20)
            .all()
        )
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for c, h in rows:
            cid = str(c.id)
            if cid in seen:
                continue
            seen.add(cid)
            out.append(
                {
                    **_company_summary(c),
                    "quantity": float(h.quantity) if h.quantity is not None else None,
                }
            )
        return out

    def _asymmetric_feed(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = (
            self.db.query(CompanyTheme, Company)
            .join(Company, CompanyTheme.company_id == Company.id)
            .filter(CompanyTheme.is_active.is_(True))
            .filter(CompanyTheme.is_asymmetric.is_(True))
            .order_by(desc(CompanyTheme.impact_score))
            .limit(limit)
            .all()
        )
        return [
            {
                **_company_summary(c),
                "theme": t.theme_name,
                "impact_score": float(t.impact_score) if t.impact_score is not None else None,
                "exposure_type": t.exposure_type,
                "reasoning": (t.reasoning or "")[:300],
            }
            for t, c in rows
        ]

    def _timeline_recent(self, days: int = 7, limit: int = 12) -> list[dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = (
            self.db.query(Filing, Company)
            .join(Company, Company.id == Filing.company_id)
            .filter(Filing.filing_date >= cutoff.date())
            .order_by(Filing.filing_date.desc())
            .limit(limit)
            .all()
        )
        out = []
        for f, c in rows:
            summary = None
            try:
                from src.db.models import FilingSummary

                fs = (
                    self.db.query(FilingSummary)
                    .filter(FilingSummary.filing_id == f.id)
                    .first()
                )
                if fs and fs.summary_one_liner:
                    summary = fs.summary_one_liner
            except Exception:
                pass
            if not summary:
                summary = f"{f.filing_type} filed on {f.filing_date.isoformat() if f.filing_date else '?'}"
            out.append(
                {
                    "filing_id": str(f.id),
                    "company_id": str(c.id),
                    "company_name": c.name,
                    "ticker_nse": c.ticker_nse,
                    "filing_type": f.filing_type,
                    "filing_date": f.filing_date.isoformat() if f.filing_date else None,
                    "summary": summary,
                }
            )
        return out

    def _suggestions(self, user: User, limit: int = 8) -> list[dict[str, Any]]:
        sectors = getattr(user, "sectors_of_interest", None) or []
        q = self.db.query(Company).filter(Company.listing_status == "active")
        if sectors:
            q = q.filter(Company.sector.in_(sectors))
        rows = (
            q.order_by(Company.market_cap_inr.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [_company_summary(c) for c in rows]
