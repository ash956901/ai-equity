"""Shared middleware registration."""

import logging
import time
import os
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.request_context import clear_request_context, set_request_id
from src.config import get_settings

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


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF double-submit cookie on mutating requests."""

    EXEMPT_PATHS = {
        "/auth/send-otp",
        "/auth/verify-otp",
        "/auth/register",
        "/auth/login",
        "/auth/demo",
        "/auth/refresh",
        "/health",
        "/",
        "/api/v1/status",
    }

    async def dispatch(self, request: Request, call_next):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        if path in self.EXEMPT_PATHS or path.startswith("/uploads"):
            return await call_next(request)

        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("x-csrf-token")

        if not cookie_token or not header_token:
            return Response(
                content='{"detail":"Missing CSRF token"}',
                status_code=403,
                media_type="application/json",
            )

        import secrets

        if not secrets.compare_digest(cookie_token, header_token):
            return Response(
                content='{"detail":"Invalid CSRF token"}',
                status_code=403,
                media_type="application/json",
            )

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Attach middleware stack to the FastAPI app."""
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(CSRFMiddleware)

    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    if os.getenv("APP_ENV") == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
