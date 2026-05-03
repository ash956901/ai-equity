"""ETL operational guardrails: rate limiting, kill switches, robots.txt audit.

Designed to be cheap and import-free so any crawler/task can wrap a request
without pulling in heavy dependencies. Falls back to in-process counters when
Redis is unavailable.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from src.config import get_settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Rate limiting (Redis token bucket with in-process fallback)                #
# --------------------------------------------------------------------------- #


class RateLimiter:
    """Token-bucket rate limiter keyed by source name.

    Uses Redis when available so workers across a cluster share the bucket;
    otherwise an in-process bucket per worker. ``acquire`` blocks (sleeps) up
    to ``timeout`` seconds when the bucket is empty.
    """

    _local_buckets: dict[str, list[float]] = {}
    _local_lock = threading.Lock()

    def __init__(self, source_name: str, rpm: int, burst: Optional[int] = None) -> None:
        self.source_name = source_name
        self.rpm = max(1, int(rpm))
        self.burst = max(self.rpm, int(burst) if burst else self.rpm * 2)
        self._redis = self._get_redis()

    @staticmethod
    def _get_redis():
        try:
            import redis  # type: ignore

            settings = get_settings()
            url = settings.redis_url or settings.celery_broker_url
            if not url:
                return None
            client = redis.from_url(url, socket_timeout=1.0, socket_connect_timeout=1.0)
            client.ping()
            return client
        except Exception:
            return None

    # ----------- public API -----------

    def acquire(self, timeout: float = 5.0) -> bool:
        """Try to acquire one token. Returns True if acquired within timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._try_consume_one():
                return True
            time.sleep(0.25)
        logger.warning("RateLimiter timeout for %s (rpm=%d)", self.source_name, self.rpm)
        return False

    # ----------- impls -----------

    def _try_consume_one(self) -> bool:
        if self._redis is not None:
            return self._try_consume_redis()
        return self._try_consume_local()

    def _try_consume_redis(self) -> bool:
        key = f"etl:ratelimit:{self.source_name}"
        try:
            count = self._redis.get(key)
            if count is None:
                self._redis.set(key, 1, ex=60)
                return True
            count = int(count)
            if count >= self.burst:
                return False
            self._redis.incr(key)
            return True
        except Exception as exc:
            logger.debug("Redis rate-limit fallback: %s", exc)
            return self._try_consume_local()

    def _try_consume_local(self) -> bool:
        now = time.time()
        with self._local_lock:
            bucket = self._local_buckets.setdefault(self.source_name, [])
            cutoff = now - 60.0
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= self.burst:
                return False
            bucket.append(now)
            return True


# --------------------------------------------------------------------------- #
#  Kill switches                                                              #
# --------------------------------------------------------------------------- #


def is_source_disabled(source_name: str) -> bool:
    """Returns True if a given source is muted (env var or settings)."""
    raw = os.getenv("ETL_DISABLED_SOURCES", "")
    disabled = {s.strip() for s in raw.split(",") if s.strip()}
    return source_name in disabled


# --------------------------------------------------------------------------- #
#  Robots.txt audit                                                           #
# --------------------------------------------------------------------------- #


_robots_cache: dict[str, Tuple[float, RobotFileParser]] = {}
_robots_lock = threading.Lock()
_ROBOTS_TTL = 3600  # 1h


def can_fetch(url: str, user_agent: str = "EquityResearchBot/1.0") -> bool:
    """robots.txt-aware fetch check. Falls back to allow-on-error so we don't
    silently disable everything when the host blocks robots.txt itself.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return True
    base = f"{parsed.scheme}://{parsed.netloc}"
    now = time.time()

    with _robots_lock:
        cached = _robots_cache.get(base)
        if cached and cached[0] > now:
            rp = cached[1]
        else:
            rp = RobotFileParser()
            rp.set_url(base + "/robots.txt")
            try:
                rp.read()
            except Exception as exc:
                logger.debug("robots.txt fetch failed for %s: %s", base, exc)
                _robots_cache[base] = (now + _ROBOTS_TTL, rp)
                return True
            _robots_cache[base] = (now + _ROBOTS_TTL, rp)

    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


# --------------------------------------------------------------------------- #
#  ETL run metadata helpers                                                   #
# --------------------------------------------------------------------------- #


def metadata_with_quota(
    base: dict, source_name: str, requests: int, errors: int, retries: int = 0
) -> dict:
    """Append quota/source telemetry to ETLRun.metadata."""
    out = dict(base or {})
    out.setdefault("sources", {})
    out["sources"][source_name] = {
        "requests": requests,
        "errors": errors,
        "retries": retries,
    }
    return out
