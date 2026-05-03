"""Tools for macro / commodity / FX series."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.db.database import get_db
from src.db.models import CommoditySeries, MacroSeries, SectorCommodityLink


def _serialize_series(rows) -> List[Dict[str, Any]]:
    return [
        {
            "code": r.code,
            "label": r.series_label,
            "date": r.observation_date.isoformat() if r.observation_date else None,
            "value": float(r.value) if r.value is not None else None,
            "unit": r.unit,
            "source": r.source,
        }
        for r in rows
    ]


@tool
def get_macro_series(
    codes: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return macro time-series observations.

    Args:
        codes: Comma-separated series codes (e.g. "DGS10,CPIAUCSL").
        start: ISO date YYYY-MM-DD (default 90 days ago).
        end: ISO date YYYY-MM-DD (default today).
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return [{"error": "no codes provided"}]
    start_d = date.fromisoformat(start) if start else date.today() - timedelta(days=90)
    end_d = date.fromisoformat(end) if end else date.today()
    db = next(get_db())
    try:
        rows = (
            db.query(MacroSeries)
            .filter(MacroSeries.code.in_(code_list))
            .filter(MacroSeries.observation_date >= start_d)
            .filter(MacroSeries.observation_date <= end_d)
            .order_by(MacroSeries.code.asc(), MacroSeries.observation_date.asc())
            .all()
        )
        return _serialize_series(rows)
    finally:
        db.close()


@tool
def get_commodity_series(
    codes: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return commodity / FX time-series observations.

    Args:
        codes: Comma-separated codes (e.g. "BRENT_FUT,SUGAR_FUT,USDINR").
        start: ISO date YYYY-MM-DD (default 30 days ago).
        end: ISO date YYYY-MM-DD (default today).
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return [{"error": "no codes provided"}]
    start_d = date.fromisoformat(start) if start else date.today() - timedelta(days=30)
    end_d = date.fromisoformat(end) if end else date.today()
    db = next(get_db())
    try:
        rows = (
            db.query(CommoditySeries)
            .filter(CommoditySeries.code.in_(code_list))
            .filter(CommoditySeries.observation_date >= start_d)
            .filter(CommoditySeries.observation_date <= end_d)
            .order_by(CommoditySeries.code.asc(), CommoditySeries.observation_date.asc())
            .all()
        )
        return _serialize_series(rows)
    finally:
        db.close()


@tool
def commodity_exposure(commodity_code: str) -> List[Dict[str, Any]]:
    """Return sector/industry/company exposure to a commodity.

    Args:
        commodity_code: Code from sources.yaml (e.g. "SUGAR_FUT", "BRENT_FUT").
    """
    db = next(get_db())
    try:
        rows = (
            db.query(SectorCommodityLink)
            .filter(SectorCommodityLink.commodity_code == commodity_code)
            .all()
        )
        return [
            {
                "scope_type": r.scope_type,
                "scope_value": r.scope_value,
                "company_id": str(r.company_id) if r.company_id else None,
                "role": r.role,
                "weight": float(r.weight) if r.weight is not None else None,
                "notes": r.notes,
            }
            for r in rows
        ]
    finally:
        db.close()
