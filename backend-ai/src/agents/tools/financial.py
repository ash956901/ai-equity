"""Financial analysis tools wrapping FinancialService."""

from datetime import date
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.agents.tools._utils import resolve_company_id
from src.db.database import get_db


@tool
def get_latest_financials(company_id: str, periods: int = 4) -> Dict[str, Any]:
    """Get latest financial statements for a company.

    Args:
        company_id: Company UUID or name/ticker (e.g. "TCS", "Infosys")
        periods: Number of recent quarters to fetch
    """
    from src.services.financial_service import FinancialService

    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return {"error": str(e)}
        service = FinancialService(db)
        try:
            result = service.get_latest_financials(uid, periods)
            if not result or not result.get("periods"):
                return {"error": f"FMP API returned empty financials for {company_id}. Tell the user data is temporarily unavailable."}
            return result
        except Exception as e:
            return {"error": f"FMP API fetch failed: {str(e)}"}
    finally:
        db.close()


@tool
def calculate_ratios(
    company_id: str, period: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate financial ratios (PE, PB, ROE, margins, leverage) for a company.

    Checks cached FinancialRatio table first (populated during ETL),
    falls back to FMP API on cache miss.

    Args:
        company_id: Company UUID or name/ticker (e.g. "TCS", "Infosys")
        period: Period end date YYYY-MM-DD (optional, defaults to latest)
    """
    from datetime import date, datetime, timedelta
    from src.services.financial_service import FinancialService
    from src.db.models import FinancialRatio

    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return {"error": str(e)}

        # Check cache first (ratios computed within last 24h)
        cache_cutoff = datetime.utcnow() - timedelta(hours=24)
        cached = (
            db.query(FinancialRatio)
            .filter(
                FinancialRatio.company_id == uid,
                FinancialRatio.created_at >= cache_cutoff,
            )
            .order_by(FinancialRatio.period_end.desc())
            .first()
        )

        if cached:
            return {
                "company_id": str(uid),
                "period_end": cached.period_end.isoformat(),
                "source": "cache",
                "ratios": {
                    "roe": float(cached.roe) if cached.roe else None,
                    "gross_margin": float(cached.gross_margin) if cached.gross_margin else None,
                    "ebitda_margin": float(cached.ebitda_margin) if cached.ebitda_margin else None,
                    "net_margin": float(cached.net_margin) if cached.net_margin else None,
                    "debt_to_equity": float(cached.debt_to_equity) if cached.debt_to_equity else None,
                    "interest_coverage": float(cached.interest_coverage) if cached.interest_coverage else None,
                    "current_ratio": float(cached.current_ratio) if cached.current_ratio else None,
                    "pe_ratio": float(cached.pe_ratio) if cached.pe_ratio else None,
                    "pb_ratio": float(cached.pb_ratio) if cached.pb_ratio else None,
                    "revenue_growth_yoy": float(cached.revenue_growth_yoy) if cached.revenue_growth_yoy else None,
                    "pat_growth_yoy": float(cached.pat_growth_yoy) if cached.pat_growth_yoy else None,
                },
            }

        # Cache miss — fall back to FMP API
        service = FinancialService(db)
        try:
            p = date.fromisoformat(period) if period else None
            result = service.calculate_ratios(uid, p)
            if not result or not result.get("ratios"):
                return {"error": f"FMP API returned empty ratios for {company_id}. Tell the user data is temporarily unavailable."}
            return result
        except Exception as e:
            return {"error": f"FMP API or calculation failed: {str(e)}"}
    finally:
        db.close()


@tool
def detect_risk_flags(company_id: str) -> List[Dict[str, Any]]:
    """Detect financial red flags for a company based on its ratios.

    Checks cached MarketSignal table first (populated during ETL),
    falls back to real-time computation on cache miss.

    Args:
        company_id: Company UUID or name/ticker (e.g. "TCS", "Infosys")
    """
    from datetime import datetime, timedelta
    from src.services.financial_service import FinancialService
    from src.db.models import MarketSignal

    flags: List[Dict[str, Any]] = []
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return [{"error": str(e)}]

        # Check cache first (signals detected within last 24h)
        cache_cutoff = datetime.utcnow() - timedelta(hours=24)
        cached = (
            db.query(MarketSignal)
            .filter(
                MarketSignal.company_id == uid,
                MarketSignal.signal_type == "risk",
                MarketSignal.detected_at >= cache_cutoff,
            )
            .all()
        )

        if cached:
            for signal in cached:
                flags.append({
                    "flag": signal.title,
                    "severity": signal.impact_level,
                    "description": signal.summary,
                    "source": "cache",
                })
            return flags

        # Cache miss — compute in real-time
        service = FinancialService(db)
        ratio_data = service.calculate_ratios(uid)
        ratios = ratio_data.get("ratios", {})
        if not ratios:
            return flags

        checks = [
            ("debt_to_equity", lambda v: v > 2.0, "HIGH_LEVERAGE",
             lambda v: "high" if v > 4.0 else "medium",
             lambda v: f"Debt-to-equity ratio is {v:.2f} (threshold: 2.0)"),
            ("interest_coverage", lambda v: v < 1.5, "LOW_INTEREST_COVERAGE",
             lambda v: "high" if v < 1.0 else "medium",
             lambda v: f"Interest coverage is {v:.2f} (threshold: 1.5)"),
            ("current_ratio", lambda v: v < 1.0, "LIQUIDITY_RISK",
             lambda _: "medium",
             lambda v: f"Current ratio is {v:.2f} (below 1.0)"),
            ("net_margin", lambda v: v < 0, "NEGATIVE_PROFITABILITY",
             lambda _: "high",
             lambda v: f"Net margin is {v:.2%} (loss-making)"),
            ("revenue_growth_yoy", lambda v: v < -0.10, "REVENUE_DECLINE",
             lambda v: "high" if v < -0.20 else "medium",
             lambda v: f"Revenue declined {v:.1%} YoY"),
            ("pat_growth_yoy", lambda v: v < -0.20, "PROFIT_DECLINE",
             lambda v: "high" if v < -0.40 else "medium",
             lambda v: f"PAT declined {v:.1%} YoY"),
            ("roe", lambda v: v < 0.05, "LOW_ROE",
             lambda v: "low" if v >= 0 else "medium",
             lambda v: f"ROE is {v:.2%} (below 5%)"),
            ("pe_ratio", lambda v: v > 80, "HIGH_VALUATION",
             lambda _: "low",
             lambda v: f"P/E ratio is {v:.1f} (elevated valuation)"),
        ]
        for metric, condition, flag_name, severity_fn, desc_fn in checks:
            val = ratios.get(metric)
            if val is not None and condition(val):
                flags.append({
                    "flag": flag_name,
                    "severity": severity_fn(val),
                    "description": desc_fn(val),
                    "metric": metric,
                    "value": val,
                    "source": "computed",
                })
        return flags
    finally:
        db.close()
