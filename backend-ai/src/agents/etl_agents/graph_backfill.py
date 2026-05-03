"""Phase 2: bootstrap relation_edges from existing structured data.

The Phase 1 table already exists; this job seeds it with edges we can derive
deterministically from current Postgres rows so the graph reasoning agent
has a useful starting point on day one:

- ``company`` --produces--> ``commodity`` (from ``sector_commodity_links``)
- ``company`` --consumes_input--> ``commodity`` (from ``sector_commodity_links``)
- ``company`` --part_of_sector--> ``sector`` (from ``companies.sector``)
- ``company`` --part_of_industry--> ``industry`` (from ``companies.industry``)
- ``company`` --held_in_portfolio--> ``portfolio`` (from ``holdings``)
- ``portfolio`` --owned_by--> ``user`` (from ``portfolios``)
- ``policy`` --affects_sector--> ``sector`` (from ``policies.sectors_affected``)
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import (
    Company,
    Holding,
    Policy,
    Portfolio,
    RelationEdge,
    SectorCommodityLink,
)

logger = logging.getLogger(__name__)


def _edge(db: Session, **kwargs) -> bool:
    triple = (
        kwargs["subject_type"],
        kwargs["subject_id"],
        kwargs["predicate"],
        kwargs["object_type"],
        kwargs["object_id"],
    )
    existing = (
        db.query(RelationEdge)
        .filter(
            RelationEdge.subject_type == triple[0],
            RelationEdge.subject_id == triple[1],
            RelationEdge.predicate == triple[2],
            RelationEdge.object_type == triple[3],
            RelationEdge.object_id == triple[4],
        )
        .first()
    )
    if existing:
        return False
    db.add(RelationEdge(**kwargs))
    return True


def backfill_graph_edges() -> Dict[str, Any]:
    """Run a one-shot backfill. Idempotent."""
    db: Session = SessionLocal()
    created = {
        "produces": 0,
        "consumes_input": 0,
        "part_of_sector": 0,
        "part_of_industry": 0,
        "held_in_portfolio": 0,
        "owned_by": 0,
        "affects_sector": 0,
    }
    try:
        # 1. Companies -> sector / industry
        for company in db.query(Company).filter(Company.listing_status == "active").all():
            if company.sector:
                if _edge(
                    db,
                    subject_type="company",
                    subject_id=str(company.id),
                    predicate="part_of_sector",
                    object_type="sector",
                    object_id=company.sector,
                    weight=Decimal("1.0"),
                    source="graph_backfill",
                    valid_from=datetime.utcnow(),
                ):
                    created["part_of_sector"] += 1
            if company.industry:
                if _edge(
                    db,
                    subject_type="company",
                    subject_id=str(company.id),
                    predicate="part_of_industry",
                    object_type="industry",
                    object_id=company.industry,
                    weight=Decimal("1.0"),
                    source="graph_backfill",
                    valid_from=datetime.utcnow(),
                ):
                    created["part_of_industry"] += 1

        # 2. sector_commodity_links -> produces / consumes_input
        for link in db.query(SectorCommodityLink).all():
            predicate = "produces" if link.role == "output" else "consumes_input"
            if link.role == "substitute":
                predicate = "competes_with"
            if link.role == "hedge":
                predicate = "hedges_against"
            subject_type = "company" if link.scope_type == "company" else link.scope_type
            subject_id = str(link.company_id) if link.company_id else link.scope_value
            if _edge(
                db,
                subject_type=subject_type,
                subject_id=subject_id,
                predicate=predicate,
                object_type="commodity",
                object_id=link.commodity_code,
                weight=link.weight or Decimal("0.5"),
                source=link.source or "sector_commodity_links",
                valid_from=datetime.utcnow(),
            ):
                created.setdefault(predicate, 0)
                created[predicate] += 1

        # 3. Portfolios + holdings
        for h in db.query(Holding).all():
            if _edge(
                db,
                subject_type="company",
                subject_id=str(h.company_id),
                predicate="held_in_portfolio",
                object_type="portfolio",
                object_id=str(h.portfolio_id),
                weight=Decimal("1.0"),
                source="graph_backfill",
                valid_from=datetime.utcnow(),
            ):
                created["held_in_portfolio"] += 1

        for p in db.query(Portfolio).all():
            if _edge(
                db,
                subject_type="portfolio",
                subject_id=str(p.id),
                predicate="owned_by",
                object_type="user",
                object_id=str(p.user_id),
                weight=Decimal("1.0"),
                source="graph_backfill",
                valid_from=datetime.utcnow(),
            ):
                created["owned_by"] += 1

        # 4. Policies -> sectors
        for policy in db.query(Policy).all():
            for sector in policy.sectors_affected or []:
                if not sector:
                    continue
                if _edge(
                    db,
                    subject_type="policy",
                    subject_id=policy.code,
                    predicate="affects_sector",
                    object_type="sector",
                    object_id=sector,
                    weight=Decimal("0.9"),
                    source="graph_backfill",
                    valid_from=datetime.utcnow(),
                ):
                    created["affects_sector"] += 1

        db.commit()
        return {"created": created, "status": "ok"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
