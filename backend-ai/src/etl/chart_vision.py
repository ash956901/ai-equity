"""Phase 2 (optional): vision-based chart extraction.

This module is a deliberately small stub that the platform can flip on once
the Phase 1 ETL is steady-state. It defines the contract used by the doc
parser when ``ENABLE_CHART_VISION=1`` is set in the environment, but does
not ship a default vision call so we don't burn LLM credits unintentionally.

Activation:

1. Set ``ENABLE_CHART_VISION=1``.
2. Configure ``GEMINI_API_KEY`` (or another vision-capable LLM) - the stub
   below uses Gemini Vision when the key is present, otherwise it
   short-circuits to a no-op.

The output of ``analyze_chart_image`` is a list of structured chart-series
dicts. Persistence to a ``chart_series`` table is intentionally out of
scope for this stub; record schema is sketched in plans/02 if/when we
decide to enable this feature.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def chart_vision_enabled() -> bool:
    return os.getenv("ENABLE_CHART_VISION") == "1"


def _gemini_vision_call(image_bytes: bytes, prompt: str) -> Optional[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import base64

        import requests  # type: ignore
    except ImportError:
        return None
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": encoded,
                            }
                        },
                    ]
                }
            ]
        }
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
            json=body,
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        candidates = (resp.json() or {}).get("candidates") or []
        if not candidates:
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        if not parts:
            return None
        return parts[0].get("text")
    except Exception as exc:
        logger.debug("Gemini Vision call failed: %s", exc)
        return None


def analyze_chart_image(image_bytes: bytes, *, hint: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return a list of chart-series records or an empty list when disabled.

    Each series record looks like::

        {
            "metric": "Quarterly revenue",
            "category": "Q1FY25",
            "value": 1234.5,
            "unit": "INR Cr",
            "confidence": 0.6,
        }
    """
    if not chart_vision_enabled():
        return []

    prompt = (
        "Extract the chart from the image. Return strict JSON list of "
        '{"metric": str, "category": str, "value": number, "unit": str, '
        '"confidence": 0.0-1.0}. '
        "If the image is not a chart, return []."
    )
    if hint:
        prompt += f"\nHint: {hint}"

    text = _gemini_vision_call(image_bytes, prompt)
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception as exc:
        logger.debug("Chart vision parse failed: %s", exc)
        return []
