"""Alert rule evaluator.

Walks every active ``alert_rules`` row, checks whether the underlying
condition fires *now*, and writes an ``alert_events`` row when it does.
Built to be cheap and idempotent — debounces firings via the rule's
``last_triggered_at`` and a per-rule cooldown stored in
``condition_config["cooldown_seconds"]`` (default 6 hours).

Supported `condition_type` values today (extend as new ones are added):

- ``price_above`` / ``price_below`` -- needs ``company_id`` + ``threshold``
- ``filing_new``                    -- new filing within ``lookback_minutes``
- ``sentiment_change``              -- avg news sentiment crosses ``threshold``
- ``asymmetric_theme``              -- a new asymmetric ``CompanyTheme`` appears
                                      for any of the rule's ``company_ids``

Anything else is silently skipped so the evaluator stays resilient to
forward-compatible rule shapes the UI may add later.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import (
    AlertEvent,
    AlertRule,
    Company,
    CompanyTheme,
    Filing,
    NewsArticle,
)

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 6 * 60 * 60  # 6 hours


# ---------------------------------------------------------------------- #
#  Per condition_type evaluators                                          #
# ---------------------------------------------------------------------- #


def _eval_price(
    db: Session, rule: AlertRule, *, above: bool
) -> Optional[dict[str, Any]]:
    cfg = rule.condition_config or {}
    company_id = cfg.get("company_id")
    threshold = cfg.get("threshold")
    if not company_id or threshold is None:
        return None
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return None
    # Pull the latest cached price from the realtime quote service.
    try:
        from src.services.market_data.context import MarketDataContext
        from src.services.market_data.quotes_service import QuotesService

        with MarketDataContext(db) as ctx:
            quote = QuotesService(ctx).get_quote(UUID(str(company_id)))
    except Exception as exc:
        logger.debug("price quote fetch failed for %s: %s", company_id, exc)
        return None
    price = (quote or {}).get("price") or (quote or {}).get("ltp")
    if price is None:
        return None
    try:
        price_dec = Decimal(str(price))
        threshold_dec = Decimal(str(threshold))
    except Exception:
        return None
    fired = price_dec > threshold_dec if above else price_dec < threshold_dec
    if not fired:
        return None
    return {
        "company_id": str(company_id),
        "price": float(price_dec),
        "threshold": float(threshold_dec),
        "direction": "above" if above else "below",
    }


def _eval_new_filing(
    db: Session, rule: AlertRule
) -> Optional[dict[str, Any]]:
    cfg = rule.condition_config or {}
    company_ids = cfg.get("company_ids") or (
        [cfg.get("company_id")] if cfg.get("company_id") else []
    )
    if not company_ids:
        return None
    lookback = int(cfg.get("lookback_minutes") or 60)
    cutoff = datetime.utcnow() - timedelta(minutes=lookback)
    last_fired = rule.last_triggered_at or datetime.min
    threshold = max(cutoff, last_fired)

    row = (
        db.query(Filing)
        .filter(Filing.company_id.in_(company_ids))
        .filter(Filing.created_at >= threshold)
        .order_by(Filing.created_at.desc())
        .first()
    )
    if not row:
        return None
    return {
        "filing_id": str(row.id),
        "company_id": str(row.company_id),
        "filing_type": row.filing_type,
        "filing_date": row.filing_date.isoformat() if row.filing_date else None,
    }


def _eval_sentiment_change(
    db: Session, rule: AlertRule
) -> Optional[dict[str, Any]]:
    cfg = rule.condition_config or {}
    company_id = cfg.get("company_id")
    threshold = cfg.get("threshold", -0.3)
    lookback_hours = int(cfg.get("lookback_hours") or 24)
    if not company_id:
        return None
    since = datetime.utcnow() - timedelta(hours=lookback_hours)
    rows = (
        db.query(NewsArticle.sentiment_score)
        .filter(NewsArticle.company_id == company_id)
        .filter(NewsArticle.published_at >= since)
        .filter(NewsArticle.sentiment_score.isnot(None))
        .all()
    )
    if not rows:
        return None
    scores = [float(r.sentiment_score) for r in rows if r.sentiment_score is not None]
    if not scores:
        return None
    avg = sum(scores) / len(scores)
    try:
        threshold_f = float(threshold)
    except Exception:
        threshold_f = -0.3
    if avg > threshold_f:
        return None
    return {
        "company_id": str(company_id),
        "avg_sentiment": avg,
        "samples": len(scores),
        "threshold": threshold_f,
        "lookback_hours": lookback_hours,
    }


def _eval_asymmetric_theme(
    db: Session, rule: AlertRule
) -> Optional[dict[str, Any]]:
    cfg = rule.condition_config or {}
    company_ids = cfg.get("company_ids") or (
        [cfg.get("company_id")] if cfg.get("company_id") else []
    )
    if not company_ids:
        return None
    last_fired = rule.last_triggered_at or datetime.min
    row = (
        db.query(CompanyTheme)
        .filter(CompanyTheme.company_id.in_(company_ids))
        .filter(CompanyTheme.is_active.is_(True))
        .filter(CompanyTheme.is_asymmetric.is_(True))
        .filter(CompanyTheme.detected_at > last_fired)
        .order_by(CompanyTheme.detected_at.desc())
        .first()
    )
    if not row:
        return None
    return {
        "company_id": str(row.company_id),
        "theme": row.theme_name,
        "exposure_type": row.exposure_type,
        "impact_score": float(row.impact_score) if row.impact_score is not None else None,
        "detected_at": row.detected_at.isoformat() if row.detected_at else None,
    }


_EVALUATORS = {
    "price_above": lambda db, rule: _eval_price(db, rule, above=True),
    "price_below": lambda db, rule: _eval_price(db, rule, above=False),
    "filing_new": _eval_new_filing,
    "sentiment_change": _eval_sentiment_change,
    "asymmetric_theme": _eval_asymmetric_theme,
}


# ---------------------------------------------------------------------- #
#  Public entry                                                           #
# ---------------------------------------------------------------------- #


def evaluate_rule(db: Session, rule: AlertRule) -> Optional[AlertEvent]:
    cfg = rule.condition_config or {}
    cooldown = int(cfg.get("cooldown_seconds") or DEFAULT_COOLDOWN_SECONDS)
    if (
        rule.last_triggered_at
        and (datetime.utcnow() - rule.last_triggered_at).total_seconds() < cooldown
    ):
        return None

    evaluator = _EVALUATORS.get(rule.condition_type)
    if not evaluator:
        return None
    try:
        payload = evaluator(db, rule)
    except Exception as exc:
        logger.warning(
            "alert evaluation failed (rule=%s, type=%s): %s",
            rule.id,
            rule.condition_type,
            exc,
        )
        return None
    if not payload:
        return None

    company_id_raw = payload.get("company_id")
    company_uuid = None
    if company_id_raw:
        try:
            company_uuid = UUID(str(company_id_raw))
        except Exception:
            company_uuid = None

    event = AlertEvent(
        rule_id=rule.id,
        user_id=rule.user_id,
        company_id=company_uuid,
        triggered_at=datetime.utcnow(),
        payload=payload,
        delivery_status="pending",
    )
    db.add(event)
    rule.last_triggered_at = event.triggered_at
    db.commit()
    try:
        from src.observability import record_alert_fired

        record_alert_fired(rule.condition_type)
    except Exception:
        pass
    return event


def evaluate_active_rules(*, batch_size: int = 200) -> dict[str, Any]:
    db = SessionLocal()
    fired = 0
    considered = 0
    try:
        rules = (
            db.query(AlertRule)
            .filter(AlertRule.is_active.is_(True))
            .limit(batch_size)
            .all()
        )
        for rule in rules:
            considered += 1
            try:
                event = evaluate_rule(db, rule)
                if event is not None:
                    fired += 1
            except Exception as exc:
                logger.warning("evaluate_rule outer failure for %s: %s", rule.id, exc)
        return {"considered": considered, "fired": fired}
    finally:
        db.close()


def deliver_pending_events(*, batch_size: int = 100) -> dict[str, Any]:
    """Mark pending alert_events as delivered. Wire to email/FCM/WebSocket
    in a follow-up; for now we just flip the status and timestamp so the
    backlog doesn't grow forever and the UI can render an in-app feed.
    """
    db = SessionLocal()
    delivered = 0
    try:
        rows = (
            db.query(AlertEvent)
            .filter(AlertEvent.delivery_status == "pending")
            .order_by(AlertEvent.triggered_at.asc())
            .limit(batch_size)
            .all()
        )
        for ev in rows:
            ev.delivery_status = "in_app"
            ev.delivered_at = datetime.utcnow()
            delivered += 1
        db.commit()
        return {"delivered": delivered}
    finally:
        db.close()
