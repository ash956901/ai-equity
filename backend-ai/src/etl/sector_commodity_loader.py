"""Loads sector_commodity_links.yaml into the sector_commodity_links table.

Idempotent: re-running upserts on the (scope_type, scope_value, commodity_code,
role) unique key. Run via the seed task ``etl.seed_sector_commodity_links``.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import select

from src.db.database import SessionLocal
from src.db.models import SectorCommodityLink

logger = logging.getLogger(__name__)

LINKS_PATH = Path(__file__).resolve().parent / "sector_commodity_links.yaml"


def _load_yaml() -> List[Dict[str, Any]]:
    if not LINKS_PATH.exists():
        return []
    try:
        import yaml  # type: ignore
    except ImportError:
        logger.error("PyYAML not installed - cannot load sector_commodity_links.yaml")
        return []
    with LINKS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("links", []) or []


def seed_sector_commodity_links() -> Dict[str, int]:
    """Populate sector_commodity_links from YAML.

    Returns a dict with counts: {"created": N, "updated": M, "skipped": K}.
    """
    rows = _load_yaml()
    if not rows:
        logger.warning("No sector-commodity links to seed")
        return {"created": 0, "updated": 0, "skipped": 0}

    db = SessionLocal()
    created = updated = skipped = 0
    try:
        for row in rows:
            scope_type = row.get("scope_type")
            scope_value = row.get("scope_value")
            commodity_code = row.get("commodity_code")
            role = row.get("role")
            if not (scope_type and scope_value and commodity_code and role):
                skipped += 1
                continue

            stmt = select(SectorCommodityLink).where(
                SectorCommodityLink.scope_type == scope_type,
                SectorCommodityLink.scope_value == scope_value,
                SectorCommodityLink.commodity_code == commodity_code,
                SectorCommodityLink.role == role,
            )
            existing = db.execute(stmt).scalar_one_or_none()

            weight = row.get("weight")
            weight_decimal = Decimal(str(weight)) if weight is not None else None
            notes = row.get("notes")
            source = row.get("source", "bootstrap")

            if existing is None:
                db.add(
                    SectorCommodityLink(
                        scope_type=scope_type,
                        scope_value=scope_value,
                        commodity_code=commodity_code,
                        role=role,
                        weight=weight_decimal,
                        source=source,
                        notes=notes,
                    )
                )
                created += 1
            else:
                changed = False
                if weight_decimal is not None and existing.weight != weight_decimal:
                    existing.weight = weight_decimal
                    changed = True
                if notes and existing.notes != notes:
                    existing.notes = notes
                    changed = True
                if source and existing.source != source:
                    existing.source = source
                    changed = True
                if changed:
                    updated += 1
        db.commit()
        logger.info("Sector-commodity seed: created=%d updated=%d skipped=%d", created, updated, skipped)
        return {"created": created, "updated": updated, "skipped": skipped}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_links_for_commodity(commodity_code: str) -> List[Dict[str, Any]]:
    """Return all links pointing to a given commodity (used by macro_commodity agent)."""
    db = SessionLocal()
    try:
        rows = (
            db.query(SectorCommodityLink)
            .filter(SectorCommodityLink.commodity_code == commodity_code)
            .all()
        )
        return [
            {
                "id": str(r.id),
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


def get_links_for_company(company_id: str) -> List[Dict[str, Any]]:
    """Return links for a specific company (or its sector/industry).

    Caller should pass the resolved company UUID. Falls back to sector/industry
    matches via the company's stored sector/industry values.
    """
    from src.db.models import Company

    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if company is None:
            return []
        scope_filters = [
            (SectorCommodityLink.scope_type == "company")
            & (SectorCommodityLink.company_id == company.id),
        ]
        if company.sector:
            scope_filters.append(
                (SectorCommodityLink.scope_type == "sector")
                & (SectorCommodityLink.scope_value == company.sector)
            )
        if company.industry:
            scope_filters.append(
                (SectorCommodityLink.scope_type == "industry")
                & (SectorCommodityLink.scope_value == company.industry)
            )
        from sqlalchemy import or_

        rows = (
            db.query(SectorCommodityLink)
            .filter(or_(*scope_filters))
            .all()
        )
        return [
            {
                "id": str(r.id),
                "scope_type": r.scope_type,
                "scope_value": r.scope_value,
                "commodity_code": r.commodity_code,
                "role": r.role,
                "weight": float(r.weight) if r.weight is not None else None,
            }
            for r in rows
        ]
    finally:
        db.close()
