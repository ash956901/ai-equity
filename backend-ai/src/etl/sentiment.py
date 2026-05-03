"""Lightweight sentiment + stance scoring for news and social.

Tries FinBERT (via transformers pipeline) first; falls back to a deterministic
keyword-based heuristic so the pipeline still runs in environments without
torch/transformers installed. Stance classification (bullish/bearish/neutral/
speculative) is purely keyword-based on top of the sentiment polarity.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


_BULLISH_TERMS = (
    "buy",
    "long",
    "moon",
    "rally",
    "upside",
    "target raised",
    "outperform",
    "to the moon",
    "bull",
    "loaded up",
)
_BEARISH_TERMS = (
    "sell",
    "short",
    "puts",
    "dump",
    "bearish",
    "crash",
    "downside",
    "underperform",
    "target cut",
    "exit",
)
_SPECULATIVE_TERMS = (
    "rumour",
    "rumor",
    "tip",
    "insider",
    "leak",
    "could moon",
    "ten bagger",
    "10x",
    "multibagger",
    "yolo",
)


@lru_cache(maxsize=1)
def _finbert_pipeline():
    settings = get_settings()
    try:
        from transformers import pipeline  # type: ignore

        return pipeline(
            "sentiment-analysis",
            model=settings.news_sentiment_model,
            top_k=None,
            truncation=True,
        )
    except Exception as exc:
        logger.info("FinBERT pipeline unavailable, using heuristic sentiment: %s", exc)
        return None


def _heuristic_sentiment(text: str) -> Dict[str, float]:
    """Return a pseudo-FinBERT result based on keyword polarity."""
    lowered = text.lower()
    pos = sum(1 for term in ("growth", "profit", "beat", "record", "raised", "bullish", "strong") if term in lowered)
    neg = sum(1 for term in ("loss", "decline", "miss", "fraud", "investigation", "weak", "downgrade") if term in lowered)
    if pos == 0 and neg == 0:
        return {"label": "neutral", "score": 0.0}
    if pos >= neg:
        return {"label": "positive", "score": min(0.9, 0.3 + 0.1 * (pos - neg))}
    return {"label": "negative", "score": -min(0.9, 0.3 + 0.1 * (neg - pos))}


def score_sentiment(text: str) -> Dict[str, float]:
    """Return ``{"label": positive|negative|neutral, "score": float in [-1,1]}``."""
    if not text or not text.strip():
        return {"label": "neutral", "score": 0.0}

    pipe = _finbert_pipeline()
    if pipe is None:
        return _heuristic_sentiment(text[:512])
    try:
        out = pipe(text[:512])
        if isinstance(out, list) and out and isinstance(out[0], list):
            ranked = sorted(out[0], key=lambda r: r["score"], reverse=True)
            top = ranked[0]
            label = top["label"].lower()
            score = float(top["score"])
        elif isinstance(out, list):
            label = out[0]["label"].lower()
            score = float(out[0]["score"])
        else:
            return _heuristic_sentiment(text)
        if label in ("positive", "bullish"):
            polarity = score
            label = "positive"
        elif label in ("negative", "bearish"):
            polarity = -score
            label = "negative"
        else:
            polarity = 0.0
            label = "neutral"
        return {"label": label, "score": round(polarity, 4)}
    except Exception as exc:
        logger.debug("FinBERT inference failed, falling back: %s", exc)
        return _heuristic_sentiment(text)


def classify_stance(text: str) -> str:
    """Return one of bullish, bearish, neutral, speculative."""
    if not text:
        return "neutral"
    lowered = text.lower()
    spec = sum(1 for t in _SPECULATIVE_TERMS if t in lowered)
    bullish = sum(1 for t in _BULLISH_TERMS if t in lowered)
    bearish = sum(1 for t in _BEARISH_TERMS if t in lowered)
    if spec >= 2 or (spec >= 1 and bullish + bearish == 0):
        return "speculative"
    if bullish > bearish:
        return "bullish"
    if bearish > bullish:
        return "bearish"
    return "neutral"


def detect_impact_level(text: str) -> Optional[str]:
    """Heuristic impact classification used by the news pipeline."""
    if not text:
        return None
    lowered = text.lower()
    if any(t in lowered for t in ("sebi", "regulatory", "rbi", "moratorium", "fraud", "ban")):
        return "High"
    if any(t in lowered for t in ("earnings", "results", "profit", "revenue", "guidance")):
        return "High"
    if any(t in lowered for t in ("management", "ceo", "cfo", "appoint", "resign")):
        return "Medium"
    return "Medium"


def detect_affected_dimension(text: str) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    if any(t in lowered for t in ("sebi", "regulatory", "rbi", "investigation")):
        return "regulation"
    if any(t in lowered for t in ("earnings", "results", "profit", "revenue", "guidance")):
        return "earnings"
    if any(t in lowered for t in ("management", "ceo", "cfo", "resign", "appoint")):
        return "management"
    if any(t in lowered for t in ("merger", "acquisition", "buyout", "stake")):
        return "M&A"
    return "general"


_TICKER_RX = re.compile(r"\b([A-Z]{2,8})\b")


def extract_tickers(text: str, *, universe: Optional[set] = None) -> list[str]:
    """Naive ticker extraction (NSE-style upper-case 2-8 chars)."""
    if not text:
        return []
    candidates = set(_TICKER_RX.findall(text or ""))
    blacklist = {
        "THE", "AND", "FOR", "INC", "LTD", "LLP", "LLC", "WITH", "FROM",
        "USD", "INR", "PLC", "CEO", "CFO", "BSE", "NSE", "GST", "RBI", "SEBI",
        "IPO", "FPO", "AGM", "EGM", "ESOP", "EPS", "ROE",
    }
    if universe:
        return sorted(candidates & set(universe))
    return sorted(c for c in candidates if c not in blacklist)
