"""Vision-LLM chart extraction.

For each PDF/PPT page flagged ``has_charts=true``, render the page to an
image, ask a vision LLM to extract the chart's structured data, and
persist one or more ``ChartSeries`` rows.

Gated by ``settings.enable_chart_extraction`` (default off) AND by a
configured LLM with vision support — without both, this module is a
no-op so it does not blow up cost during MVP. Heuristic fallback writes
a placeholder ChartSeries row capturing the chart's title only.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.db.models import ChartSeries

logger = logging.getLogger(__name__)


VISION_PROMPT = (
    "Extract the chart on this page as STRICT JSON.\n"
    "{\n"
    '  "title": "...",\n'
    '  "chart_type": "line|bar|pie|stacked_bar|area|scatter|other",\n'
    '  "x_axis_label": "...",\n'
    '  "y_axis_label": "...",\n'
    '  "units": "INR Cr|%|x|...",\n'
    '  "series": [\n'
    '    {"name": "Revenue", "points": [{"x": "FY22", "y": 1234.5}, ...]}\n'
    "  ]\n"
    "}\n"
    "If no chart is present, return {}. Do not invent values."
)


def _vision_available() -> bool:
    try:
        from src.config import get_settings

        s = get_settings()
        # Treat OpenAI / DeepSeek with API keys as vision-capable; Groq
        # currently lacks vision support so we skip there.
        if s.llm_provider == "openai" and s.openai_api_key:
            return True
        if s.llm_provider == "deepseek" and s.deepseek_api_key:
            return True
        return False
    except Exception:
        return False


def _config_enabled() -> bool:
    try:
        from src.config import get_settings

        s = get_settings()
        return bool(getattr(s, "enable_chart_extraction", False))
    except Exception:
        return False


def _render_pdf_page_png(pdf_bytes: bytes, page_number: int) -> Optional[bytes]:
    """Render a single PDF page to PNG bytes via PyMuPDF (1-indexed)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None
    try:
        if page_number < 1 or page_number > len(doc):
            return None
        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=150)
        return pix.tobytes("png")
    finally:
        doc.close()


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _call_vision_llm(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    """Single vision-LLM call. Returns parsed dict or None on failure."""
    if not _vision_available():
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from src.llm import get_llm

        b64 = base64.b64encode(image_bytes).decode("ascii")
        llm = get_llm(temperature=0.0)
        msgs = [
            SystemMessage(
                content=(
                    "You extract structured data from financial charts. "
                    "You never invent values not visible in the chart."
                )
            ),
            HumanMessage(
                content=[
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ]
            ),
        ]
        resp = llm.invoke(msgs)
        return _parse_json_block(getattr(resp, "content", "") or "")
    except Exception as exc:
        logger.debug("vision LLM call failed: %s", exc)
        return None


def extract_charts_for_filing(
    db,
    filing_id: UUID,
    pdf_bytes: bytes,
    pages: List[Dict[str, Any]],
) -> int:
    """Run chart extraction for every page flagged ``has_charts``.

    Returns the number of ``chart_series`` rows persisted. Always returns
    0 (and logs a single info line) when chart extraction is disabled or
    when no vision LLM is configured.
    """
    if not _config_enabled():
        return 0
    if not _vision_available():
        logger.info(
            "Chart extraction enabled but no vision-capable LLM is configured."
        )
        return 0

    persisted = 0
    model_name = ""
    try:
        from src.config import get_settings

        model_name = get_settings().get_llm_model()
    except Exception:
        pass

    # Wipe existing chart_series rows for this filing so re-runs are clean.
    db.query(ChartSeries).filter(ChartSeries.filing_id == filing_id).delete()

    for page in pages:
        if not page.get("has_charts"):
            continue
        page_no = page.get("page_number")
        if not isinstance(page_no, int):
            continue
        png = _render_pdf_page_png(pdf_bytes, page_no)
        if not png:
            continue
        result = _call_vision_llm(png)
        if not result:
            continue
        if not isinstance(result, dict) or not result:
            continue

        chart_type = (result.get("chart_type") or "other")[:40]
        title = (result.get("title") or page.get("title") or "")[:255] or None
        units = (result.get("units") or "")[:40] or None
        for series in result.get("series", []) or []:
            try:
                series_name = (series.get("name") or "")[:120] or None
                points = series.get("points") or []
                if not points:
                    continue
                cleaned_points = [
                    {"x": p.get("x"), "y": p.get("y")}
                    for p in points
                    if isinstance(p, dict)
                ]
                if not cleaned_points:
                    continue
                db.add(
                    ChartSeries(
                        filing_id=filing_id,
                        page_number=page_no,
                        chart_type=chart_type,
                        title=title,
                        series_name=series_name,
                        units=units,
                        data_points=cleaned_points,
                        extraction_model=model_name or "vision_llm",
                        extraction_confidence=Decimal("0.7"),
                    )
                )
                persisted += 1
            except Exception as exc:
                logger.debug("chart series persist failed: %s", exc)
    if persisted:
        db.commit()
    return persisted
