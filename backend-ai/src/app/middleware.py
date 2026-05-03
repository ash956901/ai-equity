"""Shared middleware registration."""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.request_context import clear_request_context, set_request_id

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach correlation IDs and isolate request-scoped context."""

    async def dispatch(self, request: Request, call_next):
        clear_request_context()
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        logger.info("request-start request_id=%s path=%s", request_id, request.url.path)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - started
            elapsed_ms = int(elapsed * 1000)
            logger.info(
                "request-end request_id=%s path=%s duration_ms=%s",
                request_id,
                request.url.path,
                elapsed_ms,
            )
            try:
                from src.observability import observe_request_latency

                observe_request_latency(
                    method=request.method,
                    path=_normalise_path(request.url.path),
                    seconds=elapsed,
                )
            except Exception:
                pass
            clear_request_context()


def _normalise_path(path: str) -> str:
    """Trim path to keep cardinality bounded for Prometheus labels."""
    if "/" not in path:
        return path
    parts = path.strip("/").split("/")
    # Keep the first 2 segments + replace UUID-ish remainder with '*'.
    if len(parts) <= 2:
        return path
    head = "/".join(parts[:2])
    rest = "/".join(parts[2:])
    if any(seg for seg in parts[2:] if "-" in seg or len(seg) > 8 and seg.replace("-", "").isalnum()):
        return f"/{head}/*"
    return f"/{head}/{rest}"


def register_middleware(app: FastAPI) -> None:
    """Attach middleware stack to the FastAPI app."""
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
