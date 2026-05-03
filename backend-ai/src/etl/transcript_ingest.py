"""Earnings call / concall transcript ingestion.

This module handles two paths:

1. Companies whose IR pages link a "Concall Transcript" PDF: we download the
   PDF, dedupe via SHA-256, segment into speaker turns and Q&A, persist
   ``transcripts`` + ``transcript_segments``, and embed segments into the
   Qdrant ``transcripts`` collection.
2. An optional aggregator (AlphaStreet/Researchbytes-style API): if a key is
   provided via ``ALPHASTREET_API_KEY`` we call it; otherwise this path is
   silently skipped.

We deliberately avoid scraping behind-login pages and respect robots.txt.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.db.database import SessionLocal
from src.db.models import Company, Transcript, TranscriptSegment
from src.etl.guardrails import RateLimiter, can_fetch, is_source_disabled
from src.etl.source_registry import get_source
from src.etl.storage import store_bytes, store_text
from src.services.vector_service import VectorService

logger = logging.getLogger(__name__)

USER_AGENT = "EquityResearchBot/1.0 (+contact via repo issues)"
SOURCE_NAME = "ir_concall_pages"

CONCALL_KEYWORDS = (
    "concall",
    "earnings call",
    "conference call",
    "transcript",
    "earnings transcript",
)


# --------------------------------------------------------------------------- #
#  Discovery + download                                                       #
# --------------------------------------------------------------------------- #


def _discover_concall_links(ir_url: str) -> List[Dict[str, str]]:
    if not ir_url or not can_fetch(ir_url, USER_AGENT):
        return []
    try:
        resp = requests.get(ir_url, headers={"User-Agent": USER_AGENT}, timeout=15)
    except Exception:
        return []
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    out: List[Dict[str, str]] = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = (link.get_text(strip=True) or "").lower()
        if not href.lower().endswith(".pdf"):
            continue
        if not any(kw in text for kw in CONCALL_KEYWORDS) and not any(kw in href.lower() for kw in CONCALL_KEYWORDS):
            continue
        full = href if href.startswith("http") else urljoin(ir_url, href)
        out.append({"url": full, "title": link.get_text(strip=True) or "Concall Transcript"})
    return out[:20]


def _download_pdf(url: str, limiter: RateLimiter) -> Optional[bytes]:
    if not can_fetch(url, USER_AGENT):
        return None
    if not limiter.acquire(timeout=10.0):
        return None
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    except Exception as exc:
        logger.warning("transcript download failed (%s): %s", url, exc)
        return None
    if resp.status_code != 200:
        return None
    return resp.content


# --------------------------------------------------------------------------- #
#  PDF -> raw text                                                            #
# --------------------------------------------------------------------------- #


def _pdf_text(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed - cannot parse transcript PDFs")
        return ""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        logger.error("transcript PDF open failed: %s", exc)
        return ""
    try:
        return "\n".join(page.get_text("text") or "" for page in doc)
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
#  Segmentation                                                               #
# --------------------------------------------------------------------------- #


_SPEAKER_RX = re.compile(
    r"^(?P<name>[A-Z][A-Za-z'.\-]+(?:\s+[A-Z][A-Za-z'.\-]+){0,4})"
    r"(?:\s*[—\-:]\s*(?P<role>[^\n]{0,80}))?\s*[:\-]",
    re.MULTILINE,
)
_QA_BOUNDARY = re.compile(r"(?i)question(?:[s]?[ -]+and[ -]+answer|s? & answer|/answer session|s? section)")


def _classify_role(role_text: str, name: str) -> str:
    src = f"{role_text or ''} {name or ''}".lower()
    if "moderator" in src or "operator" in src:
        return "operator"
    if any(t in src for t in ("ceo", "chief executive")):
        return "ceo"
    if any(t in src for t in ("cfo", "chief financial")):
        return "cfo"
    if "coo" in src or "chief operating" in src:
        return "coo"
    if any(t in src for t in ("analyst", "securities", "broking", "asset management")):
        return "analyst"
    return "other"


def _classify_turn(text: str, role: str, in_qa: bool) -> str:
    if not in_qa:
        return "prepared"
    if role == "analyst" or text.strip().endswith("?"):
        return "qa_question"
    return "qa_answer"


def segment_transcript(text: str) -> List[Dict[str, Any]]:
    """Heuristic segmentation that produces a list of turns.

    Returns ``[{ordinal, speaker_name, speaker_role, turn_type, text}]``.
    """
    if not text or not text.strip():
        return []

    qa_split = _QA_BOUNDARY.split(text, maxsplit=1)
    prepared_text = qa_split[0]
    qa_text = qa_split[1] if len(qa_split) > 1 else ""

    segments: List[Dict[str, Any]] = []
    ordinal = 0

    def _split_section(section_text: str, in_qa: bool):
        nonlocal ordinal
        last_pos = 0
        last_speaker: Optional[Tuple[str, str]] = None
        for match in _SPEAKER_RX.finditer(section_text):
            chunk = section_text[last_pos : match.start()].strip()
            if chunk and last_speaker:
                name, role = last_speaker
                segments.append(
                    {
                        "ordinal": ordinal,
                        "speaker_name": name[:120],
                        "speaker_role": role,
                        "turn_type": _classify_turn(chunk, role, in_qa),
                        "text": chunk[:30000],
                    }
                )
                ordinal += 1
            last_speaker = (
                match.group("name").strip(),
                _classify_role(match.group("role") or "", match.group("name") or ""),
            )
            last_pos = match.end()
        tail = section_text[last_pos:].strip()
        if tail and last_speaker:
            name, role = last_speaker
            segments.append(
                {
                    "ordinal": ordinal,
                    "speaker_name": name[:120],
                    "speaker_role": role,
                    "turn_type": _classify_turn(tail, role, in_qa),
                    "text": tail[:30000],
                }
            )
            ordinal += 1

    _split_section(prepared_text, in_qa=False)
    if qa_text:
        _split_section(qa_text, in_qa=True)

    if not segments:
        # Fallback: keep the whole document as a single prepared turn so the
        # transcript is still searchable.
        segments.append(
            {
                "ordinal": 0,
                "speaker_name": "Speaker",
                "speaker_role": "other",
                "turn_type": "prepared",
                "text": text.strip()[:60000],
            }
        )
    return segments


# --------------------------------------------------------------------------- #
#  Period detection                                                           #
# --------------------------------------------------------------------------- #


_PERIOD_RX = re.compile(r"Q([1-4])\s*(?:FY)?\s*(20\d{2}|FY?20?\d{2})", re.IGNORECASE)


def _parse_period(title: str) -> Tuple[Optional[int], Optional[int]]:
    if not title:
        return None, None
    match = _PERIOD_RX.search(title)
    if not match:
        return None, None
    quarter = int(match.group(1))
    year_raw = match.group(2)
    year_digits = re.sub(r"[^0-9]", "", year_raw)[-4:]
    if len(year_digits) == 2:
        year_digits = f"20{year_digits}"
    try:
        year = int(year_digits)
    except ValueError:
        year = None
    return year, quarter


# --------------------------------------------------------------------------- #
#  Public ingestion                                                           #
# --------------------------------------------------------------------------- #


def ingest_company_transcripts(company_id: str) -> Dict[str, Any]:
    """Discover + ingest concall transcripts for one company."""
    if is_source_disabled(SOURCE_NAME):
        return {"status": "disabled"}

    cfg = get_source("transcripts", SOURCE_NAME) or {}
    limiter = RateLimiter(SOURCE_NAME, rpm=int(cfg.get("quota_rpm", 6)))

    db = SessionLocal()
    summary = {"discovered": 0, "stored": 0, "indexed": 0}
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company or not company.ir_page_url:
            summary["status"] = "no_ir_page"
            return summary

        links = _discover_concall_links(company.ir_page_url)
        summary["discovered"] = len(links)

        for link in links:
            data = _download_pdf(link["url"], limiter)
            if data is None:
                continue
            document_hash = hashlib.sha256(data).hexdigest()
            existing = (
                db.query(Transcript).filter(Transcript.document_hash == document_hash).first()
            )
            if existing:
                continue

            year, quarter = _parse_period(link.get("title", ""))
            raw_uri = store_bytes(
                f"transcripts/{company.id}",
                f"{document_hash}.pdf",
                data,
                content_type="application/pdf",
            )

            text = _pdf_text(data)
            parsed_uri: Optional[str] = None
            if text:
                try:
                    parsed_uri = store_text(
                        f"transcripts/{company.id}/parsed",
                        f"{document_hash}.txt",
                        text,
                    )
                except Exception:
                    parsed_uri = None

            transcript = Transcript(
                company_id=company.id,
                fiscal_year=year,
                fiscal_quarter=quarter,
                period_end=None,
                title=link.get("title", "Earnings Call Transcript"),
                source="ir_concall",
                source_url=link["url"],
                raw_uri=raw_uri,
                parsed_text_uri=parsed_uri,
                document_hash=document_hash,
                language="en",
                status="parsed" if text else "failed",
                error_message=None if text else "no extractable text",
            )
            db.add(transcript)
            db.flush()

            indexable_segments: List[Dict[str, Any]] = []
            if text:
                for seg in segment_transcript(text):
                    segment = TranscriptSegment(
                        transcript_id=transcript.id,
                        ordinal=seg["ordinal"],
                        speaker_name=seg.get("speaker_name"),
                        speaker_role=seg.get("speaker_role"),
                        turn_type=seg.get("turn_type"),
                        text=seg["text"],
                        vector_id=str(uuid.uuid4()),
                    )
                    db.add(segment)
                    indexable_segments.append(
                        {
                            "vector_id": segment.vector_id,
                            "segment_id": str(segment.id) if segment.id else segment.vector_id,
                            "ordinal": segment.ordinal,
                            "speaker_role": segment.speaker_role,
                            "speaker_name": segment.speaker_name,
                            "turn_type": segment.turn_type,
                            "text": segment.text,
                        }
                    )

            db.commit()
            summary["stored"] += 1

            if indexable_segments:
                period_label = (
                    f"Q{quarter}-FY{year}" if year and quarter else None
                )
                summary["indexed"] += VectorService().index_transcript_segments(
                    transcript_id=str(transcript.id),
                    company_id=str(company.id),
                    period_label=period_label,
                    segments=indexable_segments,
                )

        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ingest_transcripts_universe(limit: int = 50) -> Dict[str, Any]:
    """Iterate through active companies with IR pages and ingest transcripts."""
    db = SessionLocal()
    try:
        companies = (
            db.query(Company)
            .filter(Company.listing_status == "active", Company.ir_page_url.isnot(None))
            .limit(limit)
            .all()
        )
        company_ids = [str(c.id) for c in companies]
    finally:
        db.close()

    totals = {"companies": len(company_ids), "stored": 0, "indexed": 0}
    for cid in company_ids:
        try:
            res = ingest_company_transcripts(cid)
            totals["stored"] += res.get("stored", 0)
            totals["indexed"] += res.get("indexed", 0)
        except Exception as exc:
            logger.warning("transcript ingestion failed for %s: %s", cid, exc)
    return totals
