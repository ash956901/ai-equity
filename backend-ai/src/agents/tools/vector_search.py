"""Vector search tools wrapping VectorService."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.tools import tool

from src.agents.tools._utils import emit_tool_metric, resolve_company_id
from src.db.database import get_db


@tool
def search_filings(
    company_id: str,
    query: str,
    filing_types: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Semantic search over company filings (annual reports, quarterly results, etc.).

    Args:
        company_id: Company UUID or name/ticker (e.g. "TCS", "Infosys")
        query: Search query text
        filing_types: Comma-separated filing types (e.g. "Annual_Report,Quarterly_Results")
        limit: Max results to return
    """
    emit_tool_metric("search_filings")
    from src.services.vector_service import VectorService

    db = next(get_db())
    try:
        uid = resolve_company_id(company_id, db)
    except ValueError as e:
        return [{"error": str(e)}]
    finally:
        db.close()
    svc = VectorService()
    types = filing_types.split(",") if filing_types else None
    return svc.search_company_filings(
        company_id=uid,
        query=query,
        filing_types=types,
        limit=limit,
    )


@tool
def search_news_semantic(
    query: str,
    company_id: Optional[str] = None,
    themes: Optional[str] = None,
    since_hours: int = 72,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Semantic search over the news_articles vector index.

    Args:
        query: Search query text.
        company_id: Optional company UUID or name/ticker.
        themes: Comma-separated theme codes to filter by.
        since_hours: Look-back window in hours.
        limit: Max hits.
    """
    from src.services.vector_service import VectorService

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
    theme_list = [t.strip() for t in themes.split(",") if t.strip()] if themes else None
    since_iso = (datetime.utcnow() - timedelta(hours=max(1, since_hours))).isoformat()
    return VectorService().search_news_semantic(
        query=query,
        company_id=cid,
        themes=theme_list,
        since_iso=since_iso,
        limit=limit,
    )


@tool
def search_user_upload(
    user_id: str, upload_id: str, query: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Search within a user-uploaded document (PDF, PPT, annual report).

    Args:
        user_id: User UUID as string
        upload_id: Upload UUID as string
        query: Search query
        limit: Max results to return
    """
    from src.services.vector_service import VectorService

    svc = VectorService()
    return svc.search_user_upload(
        user_id=UUID(user_id),
        upload_id=UUID(upload_id),
        query=query,
        limit=limit,
    )
