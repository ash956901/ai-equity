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
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "request-end request_id=%s path=%s duration_ms=%s",
                request_id,
                request.url.path,
                elapsed_ms,
            )
            clear_request_context()


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
