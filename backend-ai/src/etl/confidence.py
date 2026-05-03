"""Confidence-scoring framework used by every insight producer.

`confidence = w_quality * source_quality + w_recency * recency_decay(t)
            + w_corroboration * normalize(log(1 + n_sources))`

Components are returned alongside the final score so we can re-tune weights
post-hoc without recomputing the inputs.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import SourceQuality
from src.etl.source_registry import get_confidence_weights

DEFAULT_QUALITY = {
    "filing": 0.95,
    "transcript": 0.90,
    "macro": 0.85,
    "commodity": 0.80,
    "news": 0.65,
    "social": 0.40,
    "relation": 0.55,
    "theme": 0.55,
    "event": 0.65,
}


def get_source_quality(source_type: str, source_name: Optional[str] = None,
                       db: Optional[Session] = None) -> float:
    """Return the configured quality score for a source.

    Falls back to the type-level default. Source-name overrides take
    precedence (so e.g. "Reuters" outranks generic Tier-2 news).
    """
    own = db is None
    db = db or SessionLocal()
    try:
        if source_name:
            row = (
                db.query(SourceQuality)
                .filter(
                    SourceQuality.source_type == source_type,
                    SourceQuality.source_name == source_name,
                    SourceQuality.is_active.is_(True),
                )
                .first()
            )
            if row and row.quality_score is not None:
                return float(row.quality_score)
        # Type-level fallback row (source_name="*")
        row = (
            db.query(SourceQuality)
            .filter(
                SourceQuality.source_type == source_type,
                SourceQuality.source_name == "*",
                SourceQuality.is_active.is_(True),
            )
            .first()
        )
        if row and row.quality_score is not None:
            return float(row.quality_score)
        return DEFAULT_QUALITY.get(source_type, 0.5)
    finally:
        if own:
            db.close()


def recency_decay(observed_at: Optional[datetime], half_life_days: float = 7.0) -> float:
    """Half-life decay normalized to [0, 1]."""
    if not observed_at:
        return 0.5
    now = datetime.utcnow()
    if observed_at.tzinfo is not None:
        observed_at = observed_at.astimezone(timezone.utc).replace(tzinfo=None)
    age_days = max(0.0, (now - observed_at).total_seconds() / 86400.0)
    return float(math.pow(0.5, age_days / max(half_life_days, 0.1)))


def corroboration_score(n_sources: int) -> float:
    """Squash unbounded source counts into [0, 1]."""
    if n_sources <= 0:
        return 0.0
    return min(1.0, math.log1p(n_sources) / math.log1p(8.0))


def aggregate_confidence(
    evidence: Iterable[Dict[str, Any]],
    *,
    weights: Optional[Dict[str, float]] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Compute a confidence score from evidence dicts.

    Each evidence item should contain ``source_type`` (required),
    ``source_name`` (optional), ``observed_at`` (datetime or iso string).
    """
    weights = weights or get_confidence_weights()
    half_life = weights.get("recency_half_life_days", 7.0)

    own = db is None
    db = db or SessionLocal()
    try:
        items = list(evidence)
        if not items:
            return {
                "confidence": 0.0,
                "components": {
                    "source_quality": 0.0,
                    "recency": 0.0,
                    "corroboration": 0.0,
                    "n_sources": 0,
                },
            }

        quality_values: List[float] = []
        recency_values: List[float] = []
        unique_sources = set()
        for item in items:
            stype = item.get("source_type") or "news"
            sname = item.get("source_name")
            quality_values.append(get_source_quality(stype, sname, db))
            observed = item.get("observed_at")
            if isinstance(observed, str):
                try:
                    observed = datetime.fromisoformat(observed.replace("Z", "+00:00"))
                except Exception:
                    observed = None
            recency_values.append(recency_decay(observed, half_life_days=half_life))
            unique_sources.add((stype, sname or "*"))

        avg_quality = sum(quality_values) / len(quality_values)
        avg_recency = sum(recency_values) / len(recency_values)
        corroboration = corroboration_score(len(unique_sources))

        score = (
            weights.get("source_quality", 0.5) * avg_quality
            + weights.get("recency", 0.3) * avg_recency
            + weights.get("corroboration", 0.2) * corroboration
        )
        score = max(0.0, min(1.0, score))
        return {
            "confidence": round(score, 4),
            "components": {
                "source_quality": round(avg_quality, 4),
                "recency": round(avg_recency, 4),
                "corroboration": round(corroboration, 4),
                "n_sources": len(unique_sources),
                "weights": dict(weights),
            },
        }
    finally:
        if own:
            db.close()


def to_decimal(value: float) -> Decimal:
    return Decimal(str(round(value, 4)))


# --------------------------------------------------------------------------- #
#  Source-quality seed                                                        #
# --------------------------------------------------------------------------- #


SEED_QUALITY: List[Dict[str, Any]] = [
    {"source_type": "filing", "source_name": "*", "quality_score": 0.95},
    {"source_type": "transcript", "source_name": "*", "quality_score": 0.90},
    {"source_type": "macro", "source_name": "*", "quality_score": 0.85},
    {"source_type": "commodity", "source_name": "*", "quality_score": 0.80},
    {"source_type": "news", "source_name": "*", "quality_score": 0.65},
    {"source_type": "news", "source_name": "Reuters", "quality_score": 0.85},
    {"source_type": "news", "source_name": "Bloomberg", "quality_score": 0.85},
    {"source_type": "news", "source_name": "Mint", "quality_score": 0.80},
    {"source_type": "news", "source_name": "Moneycontrol", "quality_score": 0.78},
    {"source_type": "news", "source_name": "Business Standard", "quality_score": 0.78},
    {"source_type": "news", "source_name": "Economic Times", "quality_score": 0.78},
    {"source_type": "news", "source_name": "Google News", "quality_score": 0.55},
    {"source_type": "social", "source_name": "*", "quality_score": 0.40},
    {"source_type": "social", "source_name": "stocktwits", "quality_score": 0.45},
    {"source_type": "social", "source_name": "reddit", "quality_score": 0.40},
    {"source_type": "social", "source_name": "twitter", "quality_score": 0.40},
    {"source_type": "social", "source_name": "telegram", "quality_score": 0.20},
    {"source_type": "relation", "source_name": "*", "quality_score": 0.55},
    {"source_type": "theme", "source_name": "*", "quality_score": 0.55},
    {"source_type": "event", "source_name": "*", "quality_score": 0.65},
]


def seed_source_quality() -> Dict[str, int]:
    db = SessionLocal()
    created = updated = 0
    try:
        for row in SEED_QUALITY:
            existing = (
                db.query(SourceQuality)
                .filter(
                    SourceQuality.source_type == row["source_type"],
                    SourceQuality.source_name == row["source_name"],
                )
                .first()
            )
            if existing is None:
                db.add(SourceQuality(**row))
                created += 1
            else:
                if float(existing.quality_score or 0) != row["quality_score"]:
                    existing.quality_score = to_decimal(row["quality_score"])
                    updated += 1
        db.commit()
        return {"created": created, "updated": updated}
    finally:
        db.close()
