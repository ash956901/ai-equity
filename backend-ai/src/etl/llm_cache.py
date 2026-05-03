"""Redis-backed cache for LLM call results.

Used by the nightly Theme + Event + Insight agents to avoid re-paying for
identical prompts when re-running on a slow night. Keys are SHA-256 of the
prompt body; values are JSON-serialized strings with a configurable TTL.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 7 * 24 * 3600


def _redis():
    try:
        import redis  # type: ignore

        url = get_settings().redis_url or get_settings().celery_broker_url
        if not url:
            return None
        client = redis.from_url(url, socket_timeout=1.0, socket_connect_timeout=1.0)
        client.ping()
        return client
    except Exception:
        return None


def _key(prompt_body: str) -> str:
    digest = hashlib.sha256(prompt_body.encode("utf-8")).hexdigest()
    return f"etl:llm_cache:{digest}"


def get(prompt_body: str) -> Optional[Any]:
    if os.getenv("LLM_CACHE_DISABLED") == "1":
        return None
    r = _redis()
    if not r:
        return None
    try:
        raw = r.get(_key(prompt_body))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.debug("LLM cache read failed: %s", exc)
        return None


def set(prompt_body: str, value: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    if os.getenv("LLM_CACHE_DISABLED") == "1":
        return
    r = _redis()
    if not r:
        return
    try:
        r.set(_key(prompt_body), json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as exc:
        logger.debug("LLM cache write failed: %s", exc)
