"""Redis cache layer for real-time financial data."""

import json
import logging
from datetime import timedelta
from typing import Any, Optional

import redis

from src.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


class CacheTTL:
    """Default TTLs for different data types."""

    QUOTE_LTP = timedelta(seconds=15)
    QUOTE_FULL = timedelta(minutes=1)
    COMPANY_PROFILE = timedelta(hours=24)
    FINANCIALS = timedelta(hours=6)
    RATIOS = timedelta(hours=6)
    NEWS = timedelta(minutes=30)
    INSTRUMENT_MASTER = timedelta(hours=12)
    SCRAPED_DATA = timedelta(hours=4)
    USER_PROFILE = timedelta(minutes=15)
    DISCOVERY_FEED = timedelta(minutes=10)
    HOME_PERSONALIZED = timedelta(seconds=60)
    CANDLES_INTRADAY = timedelta(seconds=60)
    CANDLES_SHORT = timedelta(minutes=5)
    CANDLES_MEDIUM = timedelta(hours=1)
    CANDLES_LONG = timedelta(hours=24)


def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis client. Returns None if Redis is unavailable."""
    global _redis_client
    settings = get_settings()
    url = settings.redis_url or settings.celery_broker_url

    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None

    try:
        _redis_client = redis.from_url(url, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.debug("Redis unavailable: %s", e)
        return None


class CacheService:
    """Thin wrapper over Redis with JSON serialisation and key namespacing."""

    PREFIX = "eq:"

    def __init__(self):
        self._r = get_redis()

    @property
    def available(self) -> bool:
        return self._r is not None

    def _key(self, namespace: str, identifier: str) -> str:
        return f"{self.PREFIX}{namespace}:{identifier}"

    def get(self, namespace: str, identifier: str) -> Optional[Any]:
        if not self.available:
            self._record(namespace, hit=False)
            return None
        try:
            raw = self._r.get(self._key(namespace, identifier))
            value = json.loads(raw) if raw else None
            self._record(namespace, hit=value is not None)
            return value
        except Exception as e:
            logger.debug("Cache get error: %s", e)
            self._record(namespace, hit=False)
            return None

    @staticmethod
    def _record(namespace: str, *, hit: bool) -> None:
        try:
            from src.observability import record_cache

            record_cache(namespace, hit=hit)
        except Exception:
            pass

    def set(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        ttl: timedelta = CacheTTL.COMPANY_PROFILE,
    ) -> None:
        if not self.available:
            return
        try:
            self._r.setex(
                self._key(namespace, identifier),
                int(ttl.total_seconds()),
                json.dumps(value, default=str),
            )
        except Exception as e:
            logger.debug("Cache set error: %s", e)

    def delete(self, namespace: str, identifier: str) -> None:
        if not self.available:
            return
        try:
            self._r.delete(self._key(namespace, identifier))
        except Exception:
            pass

    def flush_namespace(self, namespace: str) -> int:
        """Delete all keys under a namespace. Returns count deleted."""
        if not self.available:
            return 0
        try:
            pattern = self._key(namespace, "*")
            keys = list(self._r.scan_iter(match=pattern, count=500))
            if keys:
                return self._r.delete(*keys)
            return 0
        except Exception:
            return 0


# ---------------------------------------------------------------------- #
# Module-level helpers used by the auth deps + W6 user-profile cache.    #
# ---------------------------------------------------------------------- #


def get_user_profile_cached(user_id: str) -> Optional[dict]:
    return CacheService().get("user_profile", str(user_id))


def set_user_profile_cached(user_id: str, payload: dict) -> None:
    CacheService().set("user_profile", str(user_id), payload, ttl=CacheTTL.USER_PROFILE)


def invalidate_user_profile(user_id: str) -> None:
    CacheService().delete("user_profile", str(user_id))
