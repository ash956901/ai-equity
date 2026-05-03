"""Tools for social/alt-data search."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.agents.tools._utils import resolve_company_id
from src.db.database import get_db


@tool
def search_social(
    query: str,
    sources: Optional[str] = None,
    company_id: Optional[str] = None,
    since_hours: int = 48,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Semantic search across recent social/alt posts.

    Args:
        query: Search text (e.g. "ethanol policy beneficiary").
        sources: Comma-separated source filter (reddit,stocktwits,twitter).
        company_id: Optional company UUID or name/ticker.
        since_hours: Look-back window in hours.
        limit: Max results.
    """
    from src.services.vector_service import VectorService

    src_list = [s.strip() for s in sources.split(",")] if sources else None
    cid: Optional[str] = None
    if company_id:
        db = next(get_db())
        try:
            try:
                cid = str(resolve_company_id(company_id, db))
            except ValueError as e:
                return [{"error": str(e)}]
        finally:
            db.close()
    since = (datetime.utcnow() - timedelta(hours=max(1, since_hours))).isoformat()
    return VectorService().search_social(
        query=query,
        sources=src_list,
        company_id=cid,
        since_iso=since,
        limit=limit,
    )
