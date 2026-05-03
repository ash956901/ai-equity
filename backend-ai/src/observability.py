"""Lightweight observability: Prometheus counters + readiness checks.

Imports of ``prometheus_client`` are lazy so the rest of the app keeps
running if the package isn't installed (e.g. dev mode without the extra
dep). The same applies to Redis / Qdrant pings in the readiness probe —
each falls back to "skipped".
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
#  Counters / histograms
# --------------------------------------------------------------------- #

_metrics_initialised = False
_AGENT_INVOCATIONS = None  # type: ignore[assignment]
_TOOL_CALLS = None  # type: ignore[assignment]
_CACHE_HITS = None  # type: ignore[assignment]
_CACHE_MISSES = None  # type: ignore[assignment]
_ETL_RUNS = None  # type: ignore[assignment]
_ALERTS_FIRED = None  # type: ignore[assignment]
_API_REQUEST_LATENCY = None  # type: ignore[assignment]


def _ensure_metrics() -> None:
    global _metrics_initialised, _AGENT_INVOCATIONS, _TOOL_CALLS
    global _CACHE_HITS, _CACHE_MISSES, _ETL_RUNS, _ALERTS_FIRED
    global _API_REQUEST_LATENCY
    if _metrics_initialised:
        return
    try:
        from prometheus_client import Counter, Histogram

        _AGENT_INVOCATIONS = Counter(
            "agent_invocations_total",
            "Total agent invocations",
            labelnames=("subagent", "outcome"),
        )
        _TOOL_CALLS = Counter(
            "tool_calls_total",
            "Total LangGraph tool calls",
            labelnames=("tool",),
        )
        _CACHE_HITS = Counter(
            "cache_hits_total",
            "Cache hits by namespace",
            labelnames=("cache",),
        )
        _CACHE_MISSES = Counter(
            "cache_misses_total",
            "Cache misses by namespace",
            labelnames=("cache",),
        )
        _ETL_RUNS = Counter(
            "etl_run_status_total",
            "ETL run terminations by pipeline + status",
            labelnames=("pipeline", "status"),
        )
        _ALERTS_FIRED = Counter(
            "alerts_fired_total",
            "Alert events written, by condition_type",
            labelnames=("condition_type",),
        )
        _API_REQUEST_LATENCY = Histogram(
            "http_request_duration_seconds",
            "End-to-end FastAPI request latency",
            labelnames=("method", "path"),
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        _metrics_initialised = True
    except Exception as exc:  # pragma: no cover
        logger.debug("prometheus-client unavailable: %s", exc)


def record_agent_invocation(subagent: str, outcome: str = "ok") -> None:
    _ensure_metrics()
    if _AGENT_INVOCATIONS is not None:
        with suppress(Exception):
            _AGENT_INVOCATIONS.labels(subagent=subagent, outcome=outcome).inc()


def record_tool_call(tool: str) -> None:
    _ensure_metrics()
    if _TOOL_CALLS is not None:
        with suppress(Exception):
            _TOOL_CALLS.labels(tool=tool).inc()


def record_cache(cache: str, *, hit: bool) -> None:
    _ensure_metrics()
    counter = _CACHE_HITS if hit else _CACHE_MISSES
    if counter is not None:
        with suppress(Exception):
            counter.labels(cache=cache).inc()


def record_etl_run(pipeline: str, status: str) -> None:
    _ensure_metrics()
    if _ETL_RUNS is not None:
        with suppress(Exception):
            _ETL_RUNS.labels(pipeline=pipeline, status=status).inc()


def record_alert_fired(condition_type: str) -> None:
    _ensure_metrics()
    if _ALERTS_FIRED is not None:
        with suppress(Exception):
            _ALERTS_FIRED.labels(condition_type=condition_type).inc()


def observe_request_latency(method: str, path: str, seconds: float) -> None:
    _ensure_metrics()
    if _API_REQUEST_LATENCY is not None:
        with suppress(Exception):
            _API_REQUEST_LATENCY.labels(method=method, path=path).observe(seconds)


# --------------------------------------------------------------------- #
#  Readiness probes
# --------------------------------------------------------------------- #


def check_postgres() -> dict[str, Any]:
    try:
        from sqlalchemy import text

        from src.db.database import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"ok": True}
        finally:
            db.close()
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}


def check_redis() -> dict[str, Any]:
    try:
        from src.services.cache_service import get_redis

        client = get_redis()
        if client is None:
            return {"ok": False, "error": "no_redis_url_or_unreachable"}
        client.ping()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}


def check_qdrant() -> dict[str, Any]:
    try:
        from src.services.vector_service import VectorService

        client = VectorService()._get_client()
        if client is None:
            return {"ok": False, "error": "qdrant_unreachable"}
        client.get_collections()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}


def aggregate_readiness() -> dict[str, Any]:
    pg = check_postgres()
    redis = check_redis()
    qdrant = check_qdrant()
    overall = pg["ok"]  # postgres is the only hard dependency
    return {
        "ready": bool(overall),
        "postgres": pg,
        "redis": redis,
        "qdrant": qdrant,
    }


# --------------------------------------------------------------------- #
#  /metrics response
# --------------------------------------------------------------------- #


def metrics_payload() -> tuple[str, bytes]:
    """Return (content_type, body). Falls back to empty if Prometheus is missing."""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return CONTENT_TYPE_LATEST, generate_latest()
    except Exception:
        return "text/plain", b""
