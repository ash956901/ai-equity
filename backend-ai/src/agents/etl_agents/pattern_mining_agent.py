"""Phase 2: Pattern Mining Agent.

Runs canned multi-hop graph traversals over ``relation_edges`` and emits
second-order insights into the same ``insights`` table the Phase 1
discovery feed reads from.

Patterns implemented:

1. policy P -> sectors S -> companies C with consumes_input edges to
   commodities X (X mandated by P).
2. event E at company A -> downstream suppliers via supplies / customer_of.
3. theme T trending up -> companies with exposed_to_theme edges + rising
   sentiment.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import (
    Company,
    CompanyTheme,
    Event,
    Insight,
    InsightEvidence,
    Policy,
    RelationEdge,
)
from src.etl.confidence import aggregate_confidence, to_decimal

logger = logging.getLogger(__name__)


def _persist_second_order_insight(
    db: Session,
    *,
    headline: str,
    narrative: str,
    primary_companies: List[Dict[str, Any]],
    related_themes: List[str],
    related_sectors: List[str],
    evidence: List[Dict[str, Any]],
    horizon_days: int = 30,
    predicted_direction: Optional[str] = None,
) -> Insight:
    confidence = aggregate_confidence(
        [
            {
                "source_type": ev.get("source_type", "relation"),
                "observed_at": datetime.utcnow(),
            }
            for ev in evidence
        ],
        db=db,
    )
    insight = Insight(
        insight_type="second_order",
        headline=headline[:500],
        narrative=narrative[:5000],
        primary_companies=primary_companies,
        related_themes=related_themes,
        related_sectors=related_sectors,
        predicted_direction=predicted_direction or "neutral",
        horizon_days=horizon_days,
        score=to_decimal(confidence["confidence"]),
        confidence=to_decimal(confidence["confidence"]),
        confidence_components=confidence["components"],
        evidence_links=evidence,
        counter_evidence=[],
        status="active",
        generated_by="PatternMiningAgent",
        generated_at=datetime.utcnow(),
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=horizon_days),
    )
    db.add(insight)
    db.flush()
    for ev in evidence:
        db.add(
            InsightEvidence(
                insight_id=insight.id,
                source_type=ev.get("source_type", "relation"),
                source_id=str(ev.get("source_id") or "")[:80],
                snippet=(ev.get("snippet") or "")[:600],
                weight=Decimal("0.6"),
            )
        )
    return insight


class PatternMiningAgent:
    """Run nightly graph traversals to surface second-order insights."""

    def run(self, *, db: Optional[Session] = None) -> Dict[str, Any]:
        own = db is None
        db = db or SessionLocal()
        summary = {"insights_created": 0, "patterns": {}}
        try:
            summary["patterns"]["policy_to_companies"] = self._policy_to_companies(db)
            summary["patterns"]["event_ripples"] = self._event_ripples(db)
            summary["patterns"]["theme_breakouts"] = self._theme_breakouts(db)
            summary["insights_created"] = sum(summary["patterns"].values())
            db.commit()
            return summary
        except Exception:
            db.rollback()
            raise
        finally:
            if own:
                db.close()

    # ------------------------------------------------------------------ #
    #  Patterns                                                          #
    # ------------------------------------------------------------------ #

    def _policy_to_companies(self, db: Session) -> int:
        """Policy -> sectors -> companies via produces/consumes_input edges."""
        created = 0
        recent_policies = (
            db.query(Policy)
            .order_by(desc(Policy.created_at))
            .limit(15)
            .all()
        )
        for policy in recent_policies:
            sectors = (
                db.query(RelationEdge)
                .filter(
                    RelationEdge.subject_type == "policy",
                    RelationEdge.subject_id == policy.code,
                    RelationEdge.predicate == "affects_sector",
                )
                .all()
            )
            if not sectors:
                continue
            sector_codes = [s.object_id for s in sectors]
            companies = (
                db.query(RelationEdge)
                .filter(
                    RelationEdge.subject_type == "company",
                    RelationEdge.predicate.in_(("part_of_sector", "part_of_industry")),
                    RelationEdge.object_id.in_(sector_codes),
                )
                .limit(20)
                .all()
            )
            if not companies:
                continue
            evidence = [
                {
                    "source_type": "policy",
                    "source_id": policy.code,
                    "snippet": policy.summary or policy.name,
                }
            ]
            evidence.extend(
                {
                    "source_type": "relation",
                    "source_id": f"policy:{policy.code}->sector:{s.object_id}",
                    "snippet": "policy affects sector",
                }
                for s in sectors[:3]
            )
            primary = [
                {"company_id": c.subject_id, "role": "beneficiary"} for c in companies[:6]
            ]
            _persist_second_order_insight(
                db,
                headline=f"Policy '{policy.name}' second-order beneficiaries",
                narrative=(
                    f"{policy.name} (effective {policy.effective_date}). "
                    f"Affected sectors: {', '.join(sector_codes[:5])}. "
                    f"Top exposed companies via the relation graph: "
                    f"{', '.join(c.subject_id for c in companies[:6])}."
                ),
                primary_companies=primary,
                related_themes=policy.themes or [],
                related_sectors=sector_codes,
                evidence=evidence,
                horizon_days=60,
            )
            created += 1
        return created

    def _event_ripples(self, db: Session) -> int:
        created = 0
        cutoff = datetime.utcnow() - timedelta(days=10)
        recent_events = (
            db.query(Event)
            .filter(Event.is_active.is_(True))
            .filter(Event.event_type.in_(["supply_disruption", "capex"]))
            .filter(Event.created_at >= cutoff)
            .order_by(desc(Event.event_date))
            .limit(20)
            .all()
        )
        for ev in recent_events:
            if not ev.company_id:
                continue
            downstream = (
                db.query(RelationEdge)
                .filter(
                    RelationEdge.subject_type == "company",
                    RelationEdge.subject_id == str(ev.company_id),
                    RelationEdge.predicate.in_(("supplies", "customer_of")),
                )
                .limit(10)
                .all()
            )
            upstream = (
                db.query(RelationEdge)
                .filter(
                    RelationEdge.object_type == "company",
                    RelationEdge.object_id == str(ev.company_id),
                    RelationEdge.predicate.in_(("supplies", "customer_of")),
                )
                .limit(10)
                .all()
            )
            ripples = downstream + upstream
            if not ripples:
                continue
            evidence = [
                {
                    "source_type": "event",
                    "source_id": str(ev.id),
                    "snippet": ev.headline or ev.event_type,
                }
            ]
            evidence.extend(
                {
                    "source_type": "relation",
                    "source_id": f"{r.subject_id}-{r.predicate}-{r.object_id}",
                    "snippet": "supply-chain edge",
                }
                for r in ripples[:3]
            )
            primary = [
                {
                    "company_id": r.object_id if r.subject_id == str(ev.company_id) else r.subject_id,
                    "role": "downstream" if r.subject_id == str(ev.company_id) else "upstream",
                }
                for r in ripples[:6]
            ]
            _persist_second_order_insight(
                db,
                headline=f"Ripple from {ev.event_type} at source company",
                narrative=(
                    f"Event '{ev.headline}' at company {ev.company_id} on "
                    f"{ev.event_date}. Suppliers / customers identified by the "
                    f"graph: {', '.join(p['company_id'] for p in primary)}."
                ),
                primary_companies=primary,
                related_themes=[],
                related_sectors=[],
                evidence=evidence,
                horizon_days=30,
            )
            created += 1
        return created

    def _theme_breakouts(self, db: Session) -> int:
        created = 0
        since = datetime.utcnow() - timedelta(days=14)
        rising = (
            db.query(
                CompanyTheme.theme_name,
                func.count(CompanyTheme.id).label("hits"),
                func.avg(CompanyTheme.impact_score).label("avg_impact"),
            )
            .filter(CompanyTheme.detected_at >= since)
            .filter(CompanyTheme.is_active.is_(True))
            .group_by(CompanyTheme.theme_name)
            .having(func.count(CompanyTheme.id) >= 4)
            .order_by(desc("hits"))
            .limit(5)
            .all()
        )
        for theme_name, hits, avg_impact in rising:
            companies = (
                db.query(CompanyTheme, Company)
                .join(Company, CompanyTheme.company_id == Company.id)
                .filter(CompanyTheme.theme_name == theme_name)
                .filter(CompanyTheme.is_active.is_(True))
                .order_by(desc(CompanyTheme.impact_score))
                .limit(8)
                .all()
            )
            if not companies:
                continue
            primary = [
                {"company_id": str(c.id), "role": "exposed"} for _, c in companies
            ]
            evidence = [
                {
                    "source_type": "theme",
                    "source_id": theme_name,
                    "snippet": f"hits={hits}, avg_impact={float(avg_impact or 0):.2f}",
                }
            ]
            _persist_second_order_insight(
                db,
                headline=f"Rising theme '{theme_name}' - top exposed names",
                narrative=(
                    f"{hits} companies tagged with '{theme_name}' in the last 14 days "
                    f"(avg impact {float(avg_impact or 0):.2f}). Top names by impact: "
                    f"{', '.join(c.name for _, c in companies)}."
                ),
                primary_companies=primary,
                related_themes=[theme_name],
                related_sectors=list({c.sector for _, c in companies if c.sector}),
                evidence=evidence,
                horizon_days=45,
            )
            created += 1
        return created
