"""Filing document parser.

Extracts per-page text from PDFs (PyMuPDF) and PPTX (python-pptx),
persists ``filing_pages`` rows and indexes chunks into the Qdrant
``company_filings`` collection. Idempotent: re-running on the same filing
deletes prior pages first.

When the optional dependencies are present, also:
- extracts financial-statement tables via ``pdfplumber.extract_tables`` and
  persists normalised rows to ``statement_items``
- runs vision-LLM chart extraction on chart-bearing pages (gated)
"""

from __future__ import annotations

import logging
import re
import tempfile
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import Filing, FilingPage, StatementItem
from src.etl.storage import load_bytes, store_text
from src.services.vector_service import VectorService

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  PDF extraction                                                             #
# --------------------------------------------------------------------------- #


def _extract_pdf_pages(data: bytes) -> List[Dict[str, Any]]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed - cannot parse PDFs")
        return []

    pages: List[Dict[str, Any]] = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        logger.error("Failed to open PDF: %s", exc)
        return []

    try:
        for idx, page in enumerate(doc, start=1):
            text = (page.get_text("text") or "").strip()
            has_tables = False
            try:
                if hasattr(page, "find_tables"):
                    has_tables = bool(page.find_tables().tables)
            except Exception:
                has_tables = False
            has_charts = False
            try:
                images = page.get_images()
                has_charts = bool(images)
            except Exception:
                has_charts = False
            pages.append(
                {
                    "page_number": idx,
                    "title": f"Page {idx}",
                    "text": text,
                    "has_tables": has_tables,
                    "has_charts": has_charts,
                }
            )
    finally:
        doc.close()
    return pages


# --------------------------------------------------------------------------- #
#  PDF table extraction                                                       #
# --------------------------------------------------------------------------- #


# Header-keyword heuristics used to classify a table into one of the
# statement types. Keep the lists short and unambiguous.
_STATEMENT_TYPE_HEURISTICS: list[tuple[str, set[str]]] = [
    ("PL", {"revenue", "income", "ebitda", "profit", "expense", "tax", "eps"}),
    ("BS", {"assets", "liabilities", "equity", "borrowings", "share capital"}),
    ("CF", {"operating activities", "investing activities", "financing activities", "cash flow"}),
    ("SEGMENT", {"segment", "geography", "geographic", "by region"}),
    ("SHAREHOLDING", {"promoter", "pledge", "shareholding", "fii", "dii"}),
]

# Period-end pattern to detect column headers like "FY2024", "Q3 FY24",
# "31-Mar-2024", "Mar 24". We only need year + quarter granularity.
_PERIOD_PATTERNS = [
    re.compile(r"\bFY\s?(\d{2,4})\b", re.IGNORECASE),
    re.compile(r"\b(Q[1-4])\s*FY\s?(\d{2,4})\b", re.IGNORECASE),
    re.compile(r"\b(\d{2})[-\s/](Mar|Jun|Sep|Dec)\b", re.IGNORECASE),
    re.compile(r"\b(Mar|Jun|Sep|Dec)[-\s/](\d{2,4})\b", re.IGNORECASE),
    re.compile(r"\b(\d{4})\b"),
]


def _classify_statement_type(headers: list[str], body_first_col: list[str]) -> Optional[str]:
    blob = " ".join(headers + body_first_col).lower()
    best: Optional[str] = None
    best_hits = 0
    for code, keywords in _STATEMENT_TYPE_HEURISTICS:
        hits = sum(1 for k in keywords if k in blob)
        if hits > best_hits:
            best_hits = hits
            best = code
    return best if best_hits >= 2 else None


def _parse_period_end(label: str) -> Optional[date_cls]:
    """Best-effort YYYY-Mar-31 derivation from a column header label."""
    if not label:
        return None
    text = str(label).strip()
    if not text:
        return None

    # FY24 / FY2024 → 31-Mar of that year
    m = _PERIOD_PATTERNS[0].search(text)
    if m:
        yr = int(m.group(1))
        if yr < 100:
            yr += 2000
        return date_cls(yr, 3, 31)

    # Quarter (Q3 FY24) → quarter end
    m = _PERIOD_PATTERNS[1].search(text)
    if m:
        q_num = int(m.group(1)[1])
        yr = int(m.group(2))
        if yr < 100:
            yr += 2000
        # FY = Apr-Mar; Q1=Jun, Q2=Sep, Q3=Dec, Q4=Mar
        month_day = {1: (6, 30), 2: (9, 30), 3: (12, 31), 4: (3, 31)}[q_num]
        end_year = yr if q_num == 4 else yr - 1
        return date_cls(end_year if q_num != 4 else yr, month_day[0], month_day[1])

    # Mar-24 / 24-Mar / Sep 2023 etc.
    for pat in _PERIOD_PATTERNS[2:5]:
        m = pat.search(text)
        if not m:
            continue
        groups = [g for g in m.groups() if g]
        try:
            month_str = next((g for g in groups if g[:3].isalpha()), None)
            year_str = next((g for g in groups if g.isdigit()), None)
            if not year_str:
                continue
            yr = int(year_str)
            if yr < 100:
                yr += 2000
            month_map = {"mar": 3, "jun": 6, "sep": 9, "dec": 12}
            month = month_map.get(month_str.lower()[:3]) if month_str else 3
            last_day = {3: 31, 6: 30, 9: 30, 12: 31}[month or 3]
            return date_cls(yr, month or 3, last_day)
        except Exception:
            continue
    return None


def _to_decimal(cell: Any) -> Optional[Decimal]:
    """Coerce a table cell to Decimal, stripping commas / parens / units."""
    if cell is None:
        return None
    text = str(cell).strip()
    if not text or text.lower() in {"-", "n.a.", "na", "nm"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[,\s₹]", "", text.strip("()"))
    cleaned = re.sub(r"[A-Za-z%]+$", "", cleaned)
    try:
        val = Decimal(cleaned)
        return -val if negative else val
    except (InvalidOperation, ValueError):
        return None


def _extract_pdf_tables(data: bytes) -> list[dict]:
    """Use pdfplumber to extract tabular data per page. Returns a list of
    ``{page_number, headers, rows}`` dicts."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        logger.debug("pdfplumber not installed - skipping table extraction")
        return []

    out: list[dict] = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        with pdfplumber.open(tmp_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                try:
                    tables = page.extract_tables() or []
                except Exception as exc:
                    logger.debug("pdfplumber table extract page %d failed: %s", idx, exc)
                    continue
                for tbl in tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    headers = [str(c or "").strip() for c in tbl[0]]
                    rows = [
                        [str(c or "").strip() for c in row] for row in tbl[1:]
                    ]
                    out.append(
                        {"page_number": idx, "headers": headers, "rows": rows}
                    )
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass
    return out


def _persist_tables_as_statement_items(
    db: Session, filing: Filing, tables: list[dict]
) -> int:
    """Classify each extracted table and persist rows as statement_items.

    Returns the number of statement_item rows created.
    """
    if not tables:
        return 0

    db.query(StatementItem).filter(StatementItem.filing_id == filing.id).delete()

    created = 0
    for tbl in tables:
        headers = tbl.get("headers") or []
        rows = tbl.get("rows") or []
        if len(headers) < 2 or not rows:
            continue
        first_col_values = [r[0] for r in rows if r]
        st_type = _classify_statement_type(headers, first_col_values)
        if not st_type:
            continue

        # Map column index → period_end date when parseable.
        period_by_col: dict[int, date_cls] = {}
        for col_idx, h in enumerate(headers[1:], start=1):
            period = _parse_period_end(h)
            if period:
                period_by_col[col_idx] = period
        if not period_by_col:
            continue

        for row in rows:
            if not row or len(row) < 2:
                continue
            line_item = (row[0] or "").strip()
            if not line_item or len(line_item) > 240:
                continue
            for col_idx, period_end in period_by_col.items():
                if col_idx >= len(row):
                    continue
                val = _to_decimal(row[col_idx])
                if val is None:
                    continue
                db.add(
                    StatementItem(
                        company_id=filing.company_id,
                        filing_id=filing.id,
                        period_end=period_end,
                        statement_type=st_type,
                        line_item=line_item[:255],
                        value=val,
                        currency="INR",
                        units="Cr",
                        is_consolidated=True,
                    )
                )
                created += 1
    if created:
        db.commit()
    return created


# --------------------------------------------------------------------------- #
#  PPTX extraction                                                            #
# --------------------------------------------------------------------------- #


def _extract_pptx_pages(data: bytes) -> List[Dict[str, Any]]:
    try:
        from pptx import Presentation
    except ImportError:
        logger.error("python-pptx not installed - cannot parse PPTX")
        return []

    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        prs = Presentation(tmp_path)
        pages: List[Dict[str, Any]] = []
        for idx, slide in enumerate(prs.slides, start=1):
            chunks: List[str] = []
            slide_title = ""
            has_tables = False
            has_charts = False
            for shape in slide.shapes:
                if hasattr(shape, "has_text_frame") and shape.has_text_frame:
                    text = "\n".join(
                        p.text for p in shape.text_frame.paragraphs if p.text.strip()
                    )
                    if text:
                        chunks.append(text)
                if hasattr(shape, "name") and "title" in shape.name.lower():
                    if hasattr(shape, "has_text_frame") and shape.has_text_frame:
                        slide_title = shape.text_frame.text.strip() or slide_title
                if hasattr(shape, "has_table") and shape.has_table:
                    has_tables = True
                shape_type = getattr(shape, "shape_type", None)
                try:
                    from pptx.enum.shapes import MSO_SHAPE_TYPE  # type: ignore

                    if shape_type == MSO_SHAPE_TYPE.PICTURE:
                        has_charts = True
                except Exception:
                    pass
            text = "\n".join(chunks).strip()
            if not text:
                continue
            pages.append(
                {
                    "page_number": idx,
                    "title": slide_title or f"Slide {idx}",
                    "text": text,
                    "has_tables": has_tables,
                    "has_charts": has_charts,
                }
            )
        return pages
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------- #
#  Public entry                                                               #
# --------------------------------------------------------------------------- #


def parse_and_index_filing(filing_id: UUID, db: Optional[Session] = None) -> Dict[str, Any]:
    """Parse a Filing's raw bytes, write filing_pages, embed into Qdrant."""
    own_session = db is None
    db = db or SessionLocal()
    summary: Dict[str, Any] = {
        "filing_id": str(filing_id),
        "pages": 0,
        "chunks": 0,
        "status": "pending",
    }
    try:
        filing = db.query(Filing).filter(Filing.id == filing_id).first()
        if not filing:
            summary["status"] = "missing"
            return summary
        if not filing.raw_uri:
            filing.status = "failed"
            filing.error_message = "no raw_uri"
            db.commit()
            summary["status"] = "no_raw_uri"
            return summary

        data = load_bytes(filing.raw_uri)
        if data is None:
            filing.status = "failed"
            filing.error_message = "raw bytes missing"
            db.commit()
            summary["status"] = "missing_bytes"
            return summary

        url_lower = (filing.source_url or filing.raw_uri or "").lower()
        if url_lower.endswith(".pdf"):
            pages = _extract_pdf_pages(data)
        elif url_lower.endswith(".pptx") or url_lower.endswith(".ppt"):
            pages = _extract_pptx_pages(data)
        else:
            pages = _extract_pdf_pages(data)
            if not pages:
                pages = _extract_pptx_pages(data)

        if not pages:
            filing.status = "failed"
            filing.error_message = "no extractable text"
            db.commit()
            summary["status"] = "empty"
            return summary

        db.query(FilingPage).filter(FilingPage.filing_id == filing.id).delete()
        for p in pages:
            db.add(
                FilingPage(
                    filing_id=filing.id,
                    page_number=p["page_number"],
                    title=p.get("title"),
                    text=(p.get("text") or "")[:200_000],
                    has_tables=bool(p.get("has_tables")),
                    has_charts=bool(p.get("has_charts")),
                )
            )

        parsed_text = "\n\n".join(
            f"## Page {p['page_number']}\n{p.get('text','')}" for p in pages
        )
        try:
            parsed_uri = store_text(
                f"filings/{filing.company_id}/parsed",
                f"{filing.id}.md",
                parsed_text,
            )
            filing.parsed_text_uri = parsed_uri
        except Exception as exc:
            logger.warning("Failed to persist parsed text: %s", exc)

        vector_service = VectorService()
        chunks_indexed = vector_service.index_filing_pages(
            company_id=str(filing.company_id),
            filing_id=str(filing.id),
            filing_type=filing.filing_type or "Unknown",
            filing_date=filing.filing_date.isoformat() if filing.filing_date else None,
            pages=pages,
        )

        # Table extraction (PDFs only). Pure-Python; no LLM cost.
        table_rows = 0
        if url_lower.endswith(".pdf") or any(p.get("has_tables") for p in pages):
            try:
                tables = _extract_pdf_tables(data) if url_lower.endswith(".pdf") else []
                if tables:
                    table_rows = _persist_tables_as_statement_items(
                        db, filing, tables
                    )
            except Exception as exc:
                logger.warning("Table extraction failed for %s: %s", filing.id, exc)

        # Chart extraction (vision LLM). Gated by config; cheap no-op when off.
        chart_rows = 0
        if url_lower.endswith(".pdf") and any(p.get("has_charts") for p in pages):
            try:
                from src.etl.chart_extraction import extract_charts_for_filing

                chart_rows = extract_charts_for_filing(
                    db, filing.id, data, pages
                )
            except Exception as exc:
                logger.warning("Chart extraction failed for %s: %s", filing.id, exc)

        filing.status = "embedded" if chunks_indexed else "parsed"
        filing.error_message = None
        db.commit()

        summary.update(
            {
                "pages": len(pages),
                "chunks": chunks_indexed,
                "statement_items": table_rows,
                "chart_series": chart_rows,
                "status": filing.status,
            }
        )
        return summary
    except Exception as exc:
        db.rollback()
        logger.exception("parse_and_index_filing failed: %s", exc)
        try:
            filing = db.query(Filing).filter(Filing.id == filing_id).first()
            if filing:
                filing.status = "failed"
                filing.error_message = str(exc)[:500]
                db.commit()
        except Exception:
            pass
        summary["status"] = "error"
        summary["error"] = str(exc)
        return summary
    finally:
        if own_session:
            db.close()
