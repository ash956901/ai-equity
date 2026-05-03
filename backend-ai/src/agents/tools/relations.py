"""Tools for the lightweight relation_edges knowledge graph."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.db.database import get_db
from src.db.models import RelationEdge


@tool
def get_relations(
    subject_type: str,
    subject_id: str,
    predicates: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Return outbound relation edges from a subject.

    Args:
        subject_type: company | theme | policy | event | sector | commodity.
        subject_id: UUID for company, code for theme/policy/commodity, etc.
        predicates: Comma-separated predicate filter (exposed_to_theme,
            triggered_event, supplies, customer_of, ...).
        limit: Max edges.
    """
    db = next(get_db())
    try:
        query = (
            db.query(RelationEdge)
            .filter(RelationEdge.subject_type == subject_type)
            .filter(RelationEdge.subject_id == str(subject_id))
        )
        if predicates:
            preds = [p.strip() for p in predicates.split(",") if p.strip()]
            if preds:
                query = query.filter(RelationEdge.predicate.in_(preds))
        rows = query.limit(limit).all()
        return [
            {
                "subject_type": r.subject_type,
                "subject_id": r.subject_id,
                "predicate": r.predicate,
                "object_type": r.object_type,
                "object_id": r.object_id,
                "weight": float(r.weight) if r.weight is not None else None,
                "source": r.source,
                "valid_from": r.valid_from.isoformat() if r.valid_from else None,
            }
            for r in rows
        ]
    finally:
        db.close()


@tool
def reverse_relations(
    object_type: str,
    object_id: str,
    predicates: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Return inbound relation edges into an object.

    Useful for "which companies are exposed to theme X?" style queries.
    """
    db = next(get_db())
    try:
        query = (
            db.query(RelationEdge)
            .filter(RelationEdge.object_type == object_type)
            .filter(RelationEdge.object_id == str(object_id))
        )
        if predicates:
            preds = [p.strip() for p in predicates.split(",") if p.strip()]
            if preds:
                query = query.filter(RelationEdge.predicate.in_(preds))
        rows = query.limit(limit).all()
        return [
            {
                "subject_type": r.subject_type,
                "subject_id": r.subject_id,
                "predicate": r.predicate,
                "object_type": r.object_type,
                "object_id": r.object_id,
                "weight": float(r.weight) if r.weight is not None else None,
                "source": r.source,
            }
            for r in rows
        ]
    finally:
        db.close()
