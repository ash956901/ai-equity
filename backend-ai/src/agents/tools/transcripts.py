"""Tools for searching earnings call transcripts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from sqlalchemy import desc

from src.agents.tools._utils import resolve_company_id
from src.db.database import get_db
from src.db.models import Transcript, TranscriptSegment


@tool
def search_transcripts(
    query: str,
    company_id: Optional[str] = None,
    speaker_role: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Semantic search over earnings call transcript segments.

    Args:
        query: Search text (e.g. "capex guidance for FY26").
        company_id: Optional company UUID or name/ticker.
        speaker_role: Optional speaker filter (ceo, cfo, analyst, ...).
        limit: Max results.
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
    return VectorService().search_transcripts(
        query=query,
        company_id=cid,
        speaker_role=speaker_role,
        limit=limit,
    )


@tool
def list_recent_transcripts(
    company_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return recent transcript metadata for a company."""
    db = next(get_db())
    try:
        try:
            uid = resolve_company_id(company_id, db)
        except ValueError as e:
            return [{"error": str(e)}]
        rows = (
            db.query(Transcript)
            .filter(Transcript.company_id == uid)
            .order_by(desc(Transcript.created_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "transcript_id": str(r.id),
                "title": r.title,
                "fiscal_year": r.fiscal_year,
                "fiscal_quarter": r.fiscal_quarter,
                "source_url": r.source_url,
                "status": r.status,
            }
            for r in rows
        ]
    finally:
        db.close()


@tool
def get_transcript_segments(
    transcript_id: str,
    speaker_role: Optional[str] = None,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Return ordered segments for a transcript (great for QA pulling)."""
    db = next(get_db())
    try:
        query = db.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcript_id
        )
        if speaker_role:
            query = query.filter(TranscriptSegment.speaker_role == speaker_role)
        rows = query.order_by(TranscriptSegment.ordinal.asc()).limit(limit).all()
        return [
            {
                "ordinal": r.ordinal,
                "speaker_name": r.speaker_name,
                "speaker_role": r.speaker_role,
                "turn_type": r.turn_type,
                "text": (r.text or "")[:1500],
            }
            for r in rows
        ]
    finally:
        db.close()
