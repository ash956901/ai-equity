"""Macro / commodity / FX time-series ingestion.

Sources:
- FRED (US macro + Brent/WTI/USD-INR series): requires ``FRED_API_KEY``
- Yahoo Finance proxy (yfinance) for commodity futures: no key needed
- RBI: optional - we ship a minimal stub that records "no data" until an
  operator wires in the official CSV. Kill-switching it via the registry is
  cleaner than storing fake data.

Idempotency: ``(code, observation_date)`` is unique on both tables.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.config import get_settings
from src.db.database import SessionLocal
from src.db.models import CommoditySeries, MacroSeries
from src.etl.guardrails import RateLimiter, is_source_disabled
from src.etl.source_registry import get_source

logger = logging.getLogger(__name__)


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", "."):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  FRED                                                                       #
# --------------------------------------------------------------------------- #


def fetch_fred_series(code: str, *, since: Optional[date] = None) -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.fred_api_key:
        return []
    cfg = get_source("macro", "fred") or {}
    limiter = RateLimiter("fred", rpm=int(cfg.get("quota_rpm", 60)))
    if not limiter.acquire(timeout=5.0):
        return []
    params = {
        "series_id": code,
        "api_key": settings.fred_api_key,
        "file_type": "json",
    }
    if since:
        params["observation_start"] = since.isoformat()
    try:
        resp = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params=params,
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return (resp.json() or {}).get("observations", []) or []
    except Exception as exc:
        logger.debug("FRED fetch failed for %s: %s", code, exc)
        return []


def ingest_fred() -> Dict[str, int]:
    if is_source_disabled("fred"):
        return {"observations": 0, "skipped": True}
    cfg = get_source("macro", "fred") or {}
    series = cfg.get("series") or []
    if not series:
        return {"observations": 0}

    db = SessionLocal()
    inserted = 0
    try:
        since_default = date.today() - timedelta(days=365)
        for s in series:
            code = s.get("code")
            label = s.get("label") or code
            obs = fetch_fred_series(code, since=since_default)
            for row in obs:
                obs_date = row.get("date")
                value = _to_decimal(row.get("value"))
                if not obs_date:
                    continue
                stmt = (
                    pg_insert(MacroSeries)
                    .values(
                        code=code,
                        series_label=label,
                        observation_date=date.fromisoformat(obs_date),
                        value=value,
                        unit=None,
                        source="FRED",
                    )
                    .on_conflict_do_update(
                        constraint="uq_macro_series_code_date",
                        set_={"value": value, "fetched_at": datetime.utcnow()},
                    )
                )
                db.execute(stmt)
                inserted += 1
        db.commit()
        return {"observations": inserted}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --------------------------------------------------------------------------- #
#  Yahoo Finance (commodities + FX)                                           #
# --------------------------------------------------------------------------- #


def fetch_yfinance(symbol: str, *, period: str = "30d") -> List[Dict[str, Any]]:
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        logger.debug("yfinance not installed - skipping commodity ingest")
        return []
    cfg = get_source("commodity", "yfinance_commodities") or {}
    limiter = RateLimiter("yfinance_commodities", rpm=int(cfg.get("quota_rpm", 60)))
    if not limiter.acquire(timeout=5.0):
        return []
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, auto_adjust=False)
        if hist is None or hist.empty:
            return []
        out: List[Dict[str, Any]] = []
        for ts, row in hist.iterrows():
            try:
                obs_date = ts.date()
            except Exception:
                continue
            value = row.get("Close")
            if value is None:
                continue
            out.append({"date": obs_date, "value": float(value), "unit": "close"})
        return out
    except Exception as exc:
        logger.debug("yfinance fetch failed for %s: %s", symbol, exc)
        return []


def ingest_commodities() -> Dict[str, int]:
    if is_source_disabled("yfinance_commodities"):
        return {"observations": 0, "skipped": True}
    cfg = get_source("commodity", "yfinance_commodities") or {}
    series = cfg.get("series") or []
    if not series:
        return {"observations": 0}

    db = SessionLocal()
    inserted = 0
    try:
        for s in series:
            code = s.get("code")
            label = s.get("label") or code
            yf_symbol = s.get("yf_symbol")
            if not yf_symbol:
                continue
            for obs in fetch_yfinance(yf_symbol):
                stmt = (
                    pg_insert(CommoditySeries)
                    .values(
                        code=code,
                        series_label=label,
                        observation_date=obs["date"],
                        value=Decimal(str(obs["value"])),
                        unit=obs.get("unit"),
                        source="yfinance",
                    )
                    .on_conflict_do_update(
                        constraint="uq_commodity_series_code_date",
                        set_={
                            "value": Decimal(str(obs["value"])),
                            "fetched_at": datetime.utcnow(),
                        },
                    )
                )
                db.execute(stmt)
                inserted += 1
        db.commit()
        return {"observations": inserted}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --------------------------------------------------------------------------- #
#  Public API                                                                 #
# --------------------------------------------------------------------------- #


def ingest_macro_and_commodities() -> Dict[str, Any]:
    """Run a single ingestion sweep across configured macro + commodity sources."""
    fred = ingest_fred()
    commodities = ingest_commodities()
    return {"fred": fred, "commodities": commodities}


def get_recent_series_change(
    *, table: str, code: str, lookback_days: int = 7
) -> Dict[str, Any]:
    """Return the percentage change for ``code`` over the lookback window.

    ``table`` is either ``commodity`` or ``macro``.
    """
    db = SessionLocal()
    try:
        model = CommoditySeries if table == "commodity" else MacroSeries
        cutoff = date.today() - timedelta(days=lookback_days * 2)
        rows = (
            db.query(model)
            .filter(model.code == code, model.observation_date >= cutoff)
            .order_by(model.observation_date.asc())
            .all()
        )
        if len(rows) < 2 or rows[0].value is None or rows[-1].value is None:
            return {"code": code, "pct_change": None, "latest": None}
        first = float(rows[0].value)
        last = float(rows[-1].value)
        pct = ((last - first) / first) * 100.0 if first else None
        return {
            "code": code,
            "latest_date": rows[-1].observation_date.isoformat(),
            "latest_value": last,
            "pct_change": round(pct, 4) if pct is not None else None,
            "n_observations": len(rows),
        }
    finally:
        db.close()
