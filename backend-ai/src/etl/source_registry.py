"""Loader and accessor for the ETL source registry (sources.yaml).

The registry centralizes scheduling, dedup keys, storage targets, quotas,
and kill switches per source so we don't scatter them across crawlers.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).resolve().parent / "sources.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load a YAML file, falling back to an empty dict if PyYAML is missing or parse fails."""
    if not path.exists():
        logger.warning("Source registry %s not found", path)
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        logger.error("PyYAML not installed - install with `pip install pyyaml`")
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        return {}


@lru_cache(maxsize=1)
def get_registry() -> Dict[str, Any]:
    """Cached registry contents."""
    return _load_yaml(REGISTRY_PATH)


def _disabled_sources() -> set[str]:
    """Names of sources muted via ETL_DISABLED_SOURCES env var."""
    raw = os.getenv("ETL_DISABLED_SOURCES", "")
    return {s.strip() for s in raw.split(",") if s.strip()}


def get_sources(family: str) -> List[Dict[str, Any]]:
    """Return enabled source definitions for the given family (filings/news/...)."""
    reg = get_registry()
    sources = reg.get(family, []) or []
    disabled = _disabled_sources()
    out: List[Dict[str, Any]] = []
    for src in sources:
        if not src.get("enabled", True):
            continue
        if src.get("name") in disabled:
            logger.info("Source %s muted via ETL_DISABLED_SOURCES", src.get("name"))
            continue
        required_key = src.get("requires_key")
        if required_key and not os.getenv(required_key):
            logger.debug("Source %s skipped: missing %s", src.get("name"), required_key)
            continue
        out.append(src)
    return out


def get_source(family: str, name: str) -> Optional[Dict[str, Any]]:
    """Return a single source definition by name."""
    for src in get_sources(family):
        if src.get("name") == name:
            return src
    return None


def get_confidence_weights() -> Dict[str, float]:
    """Return the confidence-scoring weights configured in sources.yaml."""
    reg = get_registry()
    weights = reg.get("confidence_weights", {}) or {}
    return {
        "source_quality": float(weights.get("source_quality", 0.5)),
        "recency": float(weights.get("recency", 0.3)),
        "corroboration": float(weights.get("corroboration", 0.2)),
        "recency_half_life_days": float(weights.get("recency_half_life_days", 7)),
    }
