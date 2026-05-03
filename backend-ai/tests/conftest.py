"""Shared pytest fixtures for backend tests.

Provides a `make_authed_client` factory that mounts a router into a
fresh FastAPI app with both ``get_db`` and the auth-gate
``get_current_user`` overridden. Use it instead of building a TestClient
by hand in every test, so adding the auth dep doesn't break the suite.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient


class FakeUser:
    """Minimal stand-in for ``src.db.models.User``.

    Has the attributes ``get_current_user`` returns and ``assert_self``
    compares against — only the bits routes actually touch.
    """

    def __init__(
        self,
        *,
        user_id: Optional[UUID] = None,
        email: str = "tester@equityai.local",
        username: str = "tester",
        full_name: str = "Tester",
        expertise_level: str = "intermediate",
        is_active: bool = True,
    ) -> None:
        self.id: UUID = user_id or uuid4()
        self.email = email
        self.username = username
        self.full_name = full_name
        self.expertise_level = expertise_level
        self.risk_tolerance: Optional[str] = None
        self.investment_horizon: Optional[str] = None
        self.is_active = is_active
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.email_verified_at: Optional[datetime] = None
        self.last_login_at: Optional[datetime] = None
        self.avatar_url: Optional[str] = None
        self.theme_preference: Optional[str] = None
        self.default_chart_range: Optional[str] = None
        self.sectors_of_interest: Optional[list[str]] = None
        self.password_hash: Optional[str] = None
        self.kyc_status = "not_started"


@pytest.fixture
def fake_user() -> FakeUser:
    """Default `FakeUser` reused across tests; deterministic id per test."""
    return FakeUser()


@pytest.fixture
def make_authed_client() -> Callable[..., TestClient]:
    """Factory that returns a TestClient with both ``get_db`` and
    ``get_current_user`` already overridden.

    Usage:
        client = make_authed_client(router=auth_routes.router, user=fake_user)
    """

    def _factory(
        *,
        router: APIRouter,
        user: Optional[FakeUser] = None,
        db: Any = None,
        extra_overrides: Optional[dict] = None,
    ) -> TestClient:
        from src.db.database import get_db
        from src.domains.auth.dependencies import get_current_user

        resolved_user = user or FakeUser()
        resolved_db = db if db is not None else object()

        app = FastAPI()

        def _fake_get_db():
            yield resolved_db

        app.dependency_overrides[get_db] = _fake_get_db
        app.dependency_overrides[get_current_user] = lambda: resolved_user

        if extra_overrides:
            for dep, fn in extra_overrides.items():
                app.dependency_overrides[dep] = fn

        app.include_router(router)
        return TestClient(app)

    return _factory


@pytest.fixture
def make_anon_client() -> Callable[..., TestClient]:
    """Factory for routes that should be reachable without auth."""

    def _factory(*, router: APIRouter, db: Any = None) -> TestClient:
        from src.db.database import get_db

        resolved_db = db if db is not None else object()

        app = FastAPI()

        def _fake_get_db():
            yield resolved_db

        app.dependency_overrides[get_db] = _fake_get_db
        app.include_router(router)
        return TestClient(app)

    return _factory
