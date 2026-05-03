"""Financial analysis tools wrapping FinancialService."""

import re
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.agents.tools._utils import emit_tool_metric, resolve_company_id
from src.db.database import get_db


@tool
def get_latest_financials(company_id: str, periods: int = 4) -> Dict[str, Any]:
    """Get latest financial statements for a company.

    Args:
        company_id: Company UUID or name/ticker (e.g. "TCS", "Infosys")
        periods: Number of recent quarters to fetch
    """
    emit_tool_metric("get_latest_financials")
    from src.services.financial_service import FinancialService

    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return {"error": str(e)}
        service = FinancialService(db)
        return service.get_latest_financials(uid, periods)
    finally:
        db.close()


@tool
def calculate_ratios(
    company_id: str, period: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate financial ratios (PE, PB, ROE, margins, leverage) for a company.

    Args:
        company_id: Company UUID or name/ticker (e.g. "TCS", "Infosys")
        period: Period end date YYYY-MM-DD (optional, defaults to latest)
    """
    emit_tool_metric("calculate_ratios")
    from src.services.financial_service import FinancialService

    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return {"error": str(e)}
        service = FinancialService(db)
        p = date.fromisoformat(period) if period else None
        return service.calculate_ratios(uid, p)
    finally:
        db.close()


@tool
def detect_risk_flags(company_id: str) -> List[Dict[str, Any]]:
    """Detect financial red flags for a company based on its ratios.

    Args:
        company_id: Company UUID or name/ticker (e.g. "TCS", "Infosys")
    """
    emit_tool_metric("detect_risk_flags")
    from src.services.financial_service import FinancialService

    flags: List[Dict[str, Any]] = []
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return [{"error": str(e)}]
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
                })
        return flags
    finally:
        db.close()


# ---------------------------------------------------------------------- #
# Governance / structural risk flags                                      #
# ---------------------------------------------------------------------- #

# Filing evidence patterns. Each pattern is conservative — we want
# precision over recall so the flags surface only when the language
# really appears in disclosures.
_GOVERNANCE_PATTERNS: list[tuple[str, str, str, str]] = [
    # (flag_code, severity, description, regex)
    (
        "PROMOTER_PLEDGE",
        "high",
        "Promoter shareholding has been pledged",
        r"(?i)\bpromoter[s']?\s+(?:shares?|holdings?|stake)\s+(?:pledged|encumber)\b",
    ),
    (
        "AUDITOR_CHANGE",
        "medium",
        "Auditor change disclosed in recent filings",
        r"(?i)\b(?:resignation|change|appointment)\s+of\s+(?:the\s+)?(?:statutory\s+)?auditor\b",
    ),
    (
        "RELATED_PARTY_TRANSACTIONS",
        "medium",
        "Material related-party transactions disclosed",
        r"(?i)\brelated[-\s]party\s+transactions?\b.*?(?:material|significant|exceeding)",
    ),
    (
        "CONTINGENT_LIABILITIES",
        "medium",
        "Significant contingent liabilities disclosed",
        r"(?i)\bcontingent\s+liabilit(?:y|ies)\b.*?(?:material|significant|increased|crore)",
    ),
    (
        "QUALIFIED_OPINION",
        "high",
        "Auditor qualified opinion or emphasis of matter",
        r"(?i)\b(?:qualified\s+opinion|emphasis\s+of\s+matter|adverse\s+opinion)\b",
    ),
    (
        "DEFAULT_DISCLOSURE",
        "high",
        "Default on debt obligation disclosed",
        r"(?i)\b(?:default(?:ed)?\s+(?:on|in))\s+(?:repayment|interest|principal)",
    ),
]


def _scan_filings_for_governance(
    db, company_id, lookback_days: int = 365
) -> list[dict]:
    """Walk recent FilingPage rows looking for governance keywords."""
    from src.db.models import Filing, FilingPage

    since = date.today() - timedelta(days=lookback_days)
    pages = (
        db.query(FilingPage, Filing)
        .join(Filing, FilingPage.filing_id == Filing.id)
        .filter(Filing.company_id == company_id)
        .filter((Filing.filing_date.is_(None)) | (Filing.filing_date >= since))
        .limit(400)
        .all()
    )
    found: list[dict] = []
    seen: set[str] = set()
    for page, filing in pages:
        text = page.text or ""
        if not text:
            continue
        for code, severity, desc, pattern in _GOVERNANCE_PATTERNS:
            if code in seen:
                continue
            match = re.search(pattern, text)
            if match:
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 160)
                found.append(
                    {
                        "flag": code,
                        "severity": severity,
                        "description": desc,
                        "evidence_quote": text[start:end].strip(),
                        "filing_id": str(filing.id),
                        "filing_type": filing.filing_type,
                        "filing_date": (
                            filing.filing_date.isoformat() if filing.filing_date else None
                        ),
                        "page_number": page.page_number,
                    }
                )
                seen.add(code)
    return found


def _detect_margin_anomaly(
    db, company_id
) -> Optional[dict]:
    """Detect a sudden margin spike (>3 sigma vs trailing 8 quarters)."""
    from src.db.models import FinancialRatio

    rows = (
        db.query(FinancialRatio)
        .filter(FinancialRatio.company_id == company_id)
        .order_by(FinancialRatio.period_end.desc().nullslast())
        .limit(9)
        .all()
    )
    if len(rows) < 5:
        return None
    margins = [
        float(r.net_margin) for r in rows if r.net_margin is not None
    ]
    if len(margins) < 5:
        return None
    latest = margins[0]
    history = margins[1:]
    if not history:
        return None
    mu = mean(history)
    sigma = pstdev(history) if len(history) > 1 else 0.0
    if sigma > 0 and abs(latest - mu) > 3 * sigma:
        direction = "spike" if latest > mu else "collapse"
        return {
            "flag": "MARGIN_ANOMALY",
            "severity": "medium",
            "description": (
                f"Net margin {direction}: latest {latest:.2%} vs trailing mean "
                f"{mu:.2%} (sigma {sigma:.2%})"
            ),
            "metric": "net_margin",
            "value": latest,
            "trailing_mean": mu,
            "trailing_sigma": sigma,
        }
    return None


@tool
def detect_governance_flags(company_id: str, lookback_days: int = 365) -> List[Dict[str, Any]]:
    """Detect structural / governance red flags from filings + ratios.

    Complements ``detect_risk_flags`` (which only inspects ratios) by
    scanning recent filing pages for governance keywords (promoter pledge,
    auditor change, related-party transactions, contingent liabilities,
    qualified audit opinion, default) and computing a 3-sigma margin
    anomaly check vs the trailing 8 quarters.

    Each flag returns ``evidence_quote`` + ``filing_id`` + ``page_number``
    when sourced from a filing, so the caller can cite it.

    Args:
        company_id: Company UUID or name/ticker.
        lookback_days: How far back to scan filing pages (default 365).
    """
    emit_tool_metric("detect_governance_flags")
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return [{"error": str(e)}]
        flags = _scan_filings_for_governance(db, uid, lookback_days=lookback_days)
        anomaly = _detect_margin_anomaly(db, uid)
        if anomaly:
            flags.append(anomaly)
        return flags
    finally:
        db.close()
