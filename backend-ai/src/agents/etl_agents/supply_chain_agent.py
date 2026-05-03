"""Phase 2: Supply-chain edge miner.

Reads transcript segments + MD&A filing pages and extracts mentions like
"X sources Y from Z" or "we supply ABC to ...". Produces edges:

- ``company A`` --supplies--> ``company B`` (or industry / sector)
- ``company A`` --customer_of--> ``company B``
- ``company A`` --consumes_input--> ``commodity / product``

The extraction is heuristic-first, then LLM-tightened where available.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import (
    Company,
    Filing,
    FilingPage,
    RelationEdge,
    Transcript,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


SUPPLY_PATTERNS = [
    re.compile(r"(?:we|the company|our (?:company|business))\s+suppl(?:ies|y)\s+(?:to\s+)?([A-Z][A-Za-z0-9 .&\-]{2,60})", re.IGNORECASE),
    re.compile(r"(?:we|our (?:company|business))\s+source[s]?\s+(?:our\s+)?([A-Za-z]+)\s+from\s+([A-Z][A-Za-z0-9 .&\-]{2,60})", re.IGNORECASE),
    re.compile(r"key customer[s]? include[d]?\s+([A-Z][A-Za-z0-9 .&\-,]{4,120})", re.IGNORECASE),
    re.compile(r"primary supplier[s]? include[d]?\s+([A-Z][A-Za-z0-9 .&\-,]{4,120})", re.IGNORECASE),
]


def _resolve_company_by_name(db: Session, name: str) -> Optional[Company]:
    if not name:
        return None
    name = name.strip().rstrip(".,")
    if len(name) < 3:
        return None
    company = (
        db.query(Company)
        .filter(Company.name.ilike(f"%{name}%"))
        .first()
    )
    return company


def _extract_supply_edges(text: str) -> List[Dict[str, Any]]:
    """Run regex patterns over text; return candidate edges with raw spans."""
    edges: List[Dict[str, Any]] = []
    if not text:
        return edges
    for pat in SUPPLY_PATTERNS:
        for match in pat.finditer(text):
            edges.append(
                {
                    "predicate_hint": "supplies"
                    if "suppl" in pat.pattern.lower()
                    else (
                        "consumes_input"
                        if "source" in pat.pattern.lower()
                        else "customer_of"
                    ),
                    "groups": list(match.groups()),
                    "snippet": text[max(0, match.start() - 60) : match.end() + 60].strip(),
                }
            )
    return edges


class SupplyChainAgent:
    """Mine supply-chain edges from transcripts and MD&A pages."""

    def __init__(self, *, lookback_days: int = 60):
        self.lookback_days = lookback_days

    def run(self, *, db: Optional[Session] = None) -> Dict[str, Any]:
        own = db is None
        db = db or SessionLocal()
        summary = {"texts_scanned": 0, "edges_created": 0}
        try:
            since = datetime.utcnow() - timedelta(days=self.lookback_days)

            # 1. Transcripts (highest signal)
            seg_rows = (
                db.query(TranscriptSegment, Transcript)
                .join(Transcript, TranscriptSegment.transcript_id == Transcript.id)
                .filter(Transcript.created_at >= since)
                .limit(2000)
                .all()
            )
            for seg, tx in seg_rows:
                summary["texts_scanned"] += 1
                self._process_text(
                    db,
                    text=seg.text or "",
                    subject_company_id=tx.company_id,
                    source_id=f"transcript:{tx.id}:{seg.ordinal}",
                    summary=summary,
                )

            # 2. Filing pages (MD&A only)
            page_rows = (
                db.query(FilingPage, Filing)
                .join(Filing, FilingPage.filing_id == Filing.id)
                .filter(Filing.created_at >= since)
                .filter(Filing.filing_type.in_(["Annual_Report", "Quarterly_Results"]))
                .limit(2000)
                .all()
            )
            for page, filing in page_rows:
                summary["texts_scanned"] += 1
                self._process_text(
                    db,
                    text=page.text or "",
                    subject_company_id=filing.company_id,
                    source_id=f"filing:{filing.id}:p{page.page_number}",
                    summary=summary,
                )

            db.commit()
            return summary
        except Exception:
            db.rollback()
            raise
        finally:
            if own:
                db.close()

    def _process_text(
        self,
        db: Session,
        *,
        text: str,
        subject_company_id: Optional[UUID],
        source_id: str,
        summary: Dict[str, int],
    ) -> None:
        if not subject_company_id or not text:
            return
        for cand in _extract_supply_edges(text):
            predicate = cand.get("predicate_hint")
            groups = cand.get("groups") or []
            obj_name = groups[-1] if groups else None
            if not obj_name:
                continue
            target = _resolve_company_by_name(db, obj_name)
            if not target:
                continue
            if target.id == subject_company_id:
                continue

            triple = (
                "company",
                str(subject_company_id),
                predicate,
                "company",
                str(target.id),
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
                continue
            db.add(
                RelationEdge(
                    subject_type=triple[0],
                    subject_id=triple[1],
                    predicate=triple[2],
                    object_type=triple[3],
                    object_id=triple[4],
                    weight=Decimal("0.5"),
                    evidence_id=source_id,
                    source="supply_chain_agent",
                    valid_from=datetime.utcnow(),
                    metadata_={"snippet": cand.get("snippet", "")[:400]},
                )
            )
            summary["edges_created"] += 1
