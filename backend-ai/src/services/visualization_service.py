"""Generate publication-quality charts (PNG) for the agent's response.

Renders four core chart types using Plotly (no display server needed):

- Revenue trend (line)
- Margin trend (multi-line: gross / operating / net)
- Debt vs Equity stack (bar)
- Peer comparison (bar)

PNG bytes are persisted via ``src.etl.storage.store_bytes`` (S3 or local
file fallback) and the URI is returned. The ``QueryResponse.visualizations``
field on the API can be populated with these URIs so the UI can render them.

Falls back gracefully when Plotly + kaleido are not installed -- returns
``None`` and logs a warning so the agent can still ship its text response.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional, Sequence
from uuid import UUID

from src.db.database import SessionLocal
from src.db.models import Company, FinancialRatio, FinancialStatementRaw
from src.etl.storage import store_bytes

logger = logging.getLogger(__name__)


def _plotly_available() -> bool:
    try:
        import plotly.graph_objects as go  # noqa: F401
        import plotly.io as pio  # noqa: F401
        return True
    except ImportError:
        logger.debug("plotly not installed; visualization service is no-op")
        return False


def _persist_png(prefix: str, png_bytes: bytes) -> str:
    """Store PNG bytes and return a retrieval URI."""
    name = f"{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:10]}.png"
    return store_bytes(prefix, name, png_bytes, content_type="image/png")


def _figure_to_png(fig) -> Optional[bytes]:
    try:
        import plotly.io as pio

        return pio.to_image(fig, format="png", width=900, height=500, scale=2)
    except Exception as exc:
        logger.warning("plotly png export failed (kaleido missing?): %s", exc)
        return None


# ---------------------------------------------------------------------- #
#  Public chart helpers                                                   #
# ---------------------------------------------------------------------- #


_REVENUE_PATTERNS = ["%revenue%", "%total income%", "%net sales%"]
_DEBT_PATTERNS = ["%total debt%", "%borrowings%", "%long term debt%"]
_EQUITY_PATTERNS = ["%total equity%", "%shareholders' funds%", "%share capital and reserves%"]


def _line_item_series(
    db, company_id: UUID, statement_type: str, patterns: list[str], periods: int
) -> tuple[list[str], list[float]]:
    """Return (x_periods, y_values) summing matching line_items by period."""
    from sqlalchemy import or_

    conditions = [FinancialStatementRaw.line_item.ilike(p) for p in patterns]
    rows = (
        db.query(FinancialStatementRaw)
        .filter(FinancialStatementRaw.company_id == company_id)
        .filter(FinancialStatementRaw.statement_type == statement_type)
        .filter(or_(*conditions))
        .order_by(FinancialStatementRaw.period_end.asc())
        .all()
    )
    by_period: dict[str, float] = {}
    for r in rows:
        if r.value is None or not r.period_end:
            continue
        key = r.period_end.isoformat()
        by_period[key] = by_period.get(key, 0.0) + float(r.value)
    items = sorted(by_period.items())[-periods:]
    return [k for k, _ in items], [v for _, v in items]


def render_revenue_trend(
    company_id: UUID, *, periods: int = 8
) -> Optional[str]:
    """Line chart of total revenue across the latest N periods."""
    if not _plotly_available():
        return None
    import plotly.graph_objects as go

    db = SessionLocal()
    try:
        x_vals, y_vals = _line_item_series(
            db, company_id, "PL", _REVENUE_PATTERNS, periods
        )
        if not x_vals or not any(y_vals):
            return None
        company = db.query(Company).filter(Company.id == company_id).first()
        title = f"Revenue Trend - {company.name if company else company_id}"
        fig = go.Figure(
            data=[go.Scatter(x=x_vals, y=y_vals, mode="lines+markers", name="Revenue")]
        )
        fig.update_layout(
            title=title,
            xaxis_title="Period End",
            yaxis_title="Revenue (INR Cr)",
            template="simple_white",
        )
        png = _figure_to_png(fig)
        if not png:
            return None
        return _persist_png(f"viz/{company_id}/revenue_trend", png)
    finally:
        db.close()


def render_margin_trend(
    company_id: UUID, *, periods: int = 8
) -> Optional[str]:
    """Multi-line chart of gross / operating / net margins."""
    if not _plotly_available():
        return None
    import plotly.graph_objects as go

    db = SessionLocal()
    try:
        rows = (
            db.query(FinancialRatio)
            .filter(FinancialRatio.company_id == company_id)
            .order_by(FinancialRatio.period_end.desc())
            .limit(periods)
            .all()
        )
        if not rows:
            return None
        rows = list(reversed(rows))
        x_vals = [r.period_end.isoformat() for r in rows]
        traces = []
        for field, label in (
            ("gross_margin", "Gross Margin"),
            ("ebit_margin", "EBIT Margin"),
            ("ebitda_margin", "EBITDA Margin"),
            ("net_margin", "Net Margin"),
        ):
            ys = [
                float(getattr(r, field) or 0.0) * 100 if getattr(r, field) is not None else None
                for r in rows
            ]
            if any(y is not None and y != 0 for y in ys):
                traces.append(go.Scatter(x=x_vals, y=ys, mode="lines+markers", name=label))
        if not traces:
            return None
        company = db.query(Company).filter(Company.id == company_id).first()
        fig = go.Figure(data=traces)
        fig.update_layout(
            title=f"Margin Trend - {company.name if company else company_id}",
            xaxis_title="Period End",
            yaxis_title="Margin (%)",
            template="simple_white",
        )
        png = _figure_to_png(fig)
        if not png:
            return None
        return _persist_png(f"viz/{company_id}/margin_trend", png)
    finally:
        db.close()


def render_peer_comparison(
    company_ids: Sequence[UUID], *, metric: str = "roe"
) -> Optional[str]:
    """Bar chart comparing one ratio across peers (latest period each)."""
    if not _plotly_available() or not company_ids:
        return None
    import plotly.graph_objects as go

    db = SessionLocal()
    try:
        names: list[str] = []
        values: list[float] = []
        for cid in company_ids:
            company = db.query(Company).filter(Company.id == cid).first()
            if not company:
                continue
            ratio = (
                db.query(FinancialRatio)
                .filter(FinancialRatio.company_id == cid)
                .order_by(FinancialRatio.period_end.desc())
                .first()
            )
            if not ratio:
                continue
            val = getattr(ratio, metric, None)
            if val is None:
                continue
            names.append(company.ticker_nse or company.name)
            values.append(float(val) * (100 if metric in {"roe", "roce", "net_margin"} else 1))
        if not names:
            return None
        fig = go.Figure(data=[go.Bar(x=names, y=values, name=metric)])
        fig.update_layout(
            title=f"Peer Comparison - {metric.upper()}",
            xaxis_title="Company",
            yaxis_title=metric.upper() + (" (%)" if metric in {"roe", "roce", "net_margin"} else ""),
            template="simple_white",
        )
        png = _figure_to_png(fig)
        if not png:
            return None
        return _persist_png(f"viz/peer_comparison/{metric}", png)
    finally:
        db.close()


def render_debt_equity(
    company_id: UUID, *, periods: int = 6
) -> Optional[str]:
    """Stacked bar of total debt vs equity book value."""
    if not _plotly_available():
        return None
    import plotly.graph_objects as go

    db = SessionLocal()
    try:
        debt_x, debt_vals = _line_item_series(
            db, company_id, "BS", _DEBT_PATTERNS, periods
        )
        eq_x, eq_vals = _line_item_series(
            db, company_id, "BS", _EQUITY_PATTERNS, periods
        )
        if not (debt_vals or eq_vals):
            return None
        # Align periods on the union of (debt_x, eq_x) so the stacked bar
        # renders even when one series is sparser than the other.
        all_periods = sorted(set(debt_x) | set(eq_x))[-periods:]
        debt_map = dict(zip(debt_x, debt_vals))
        eq_map = dict(zip(eq_x, eq_vals))
        debt_aligned = [debt_map.get(p, 0.0) for p in all_periods]
        eq_aligned = [eq_map.get(p, 0.0) for p in all_periods]
        company = db.query(Company).filter(Company.id == company_id).first()
        fig = go.Figure(
            data=[
                go.Bar(name="Debt", x=all_periods, y=debt_aligned),
                go.Bar(name="Equity", x=all_periods, y=eq_aligned),
            ]
        )
        fig.update_layout(
            barmode="stack",
            title=f"Debt vs Equity - {company.name if company else company_id}",
            xaxis_title="Period End",
            yaxis_title="INR Cr",
            template="simple_white",
        )
        png = _figure_to_png(fig)
        if not png:
            return None
        return _persist_png(f"viz/{company_id}/debt_equity", png)
    finally:
        db.close()


def build_company_dashboard(company_id: UUID) -> dict[str, Any]:
    """Render the full standard chart pack for a company.

    Returns a dict with `{chart_name: uri | None}` so the agent can pick
    which to embed in its response.
    """
    return {
        "revenue_trend": render_revenue_trend(company_id),
        "margin_trend": render_margin_trend(company_id),
        "debt_equity": render_debt_equity(company_id),
    }
