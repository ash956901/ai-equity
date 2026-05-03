"""Route-level smoke tests for /auth/*. Uses AuthService monkeypatched
so we don't need a live Postgres for these fast tests."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.db.database import get_db
from src.domains.auth import routes as auth_routes
from src.domains.auth.dependencies import current_token_claims, get_current_user
from src.domains.auth.schemas import (
    CurrentUserResponse,
    SignupResponse,
    TokenPair,
)


def _fake_user_payload(user_id, email: str = "tester@equityai.local") -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user_id,
        email=email,
        username="tester",
        full_name="Tester",
        expertise_level="intermediate",
        created_at=datetime.utcnow(),
    )


class _StubAuthService:
    last_login_identifier: str | None = None
    last_signup_email: str | None = None
    forgot_called_for: str | None = None
    reset_called_with: dict | None = None
    logout_called_with: dict | None = None
    verify_token_consumed: str | None = None

    def __init__(self, db):
        self.db = db

    # ---- signup ----
    def signup(self, *, email, username, password, full_name):  # noqa: D401
        _StubAuthService.last_signup_email = email
        return SignupResponse(
            user=_fake_user_payload(uuid4(), email=email),
            tokens=TokenPair(
                access_token="access-jwt",
                refresh_token="refresh-jwt",
                expires_in=900,
            ),
            email_verification_required=False,
        )

    # ---- login ----
    def login(self, *, identifier, password):
        _StubAuthService.last_login_identifier = identifier
        return TokenPair(
            access_token="access-jwt",
            refresh_token="refresh-jwt",
            expires_in=900,
        )

    # ---- refresh ----
    def refresh(self, *, refresh_token):
        return TokenPair(
            access_token="new-access",
            refresh_token="new-refresh",
            expires_in=900,
        )

    # ---- logout ----
    def logout(self, *, access_token_jti, access_exp, refresh_jti):
        _StubAuthService.logout_called_with = {
            "access_token_jti": access_token_jti,
            "access_exp": access_exp,
            "refresh_jti": refresh_jti,
        }

    # ---- verify-email ----
    def verify_email(self, *, token):
        _StubAuthService.verify_token_consumed = token
        return _fake_user_payload(uuid4())

    def resend_verification(self, *, user_id):
        return None

    # ---- forgot/reset ----
    def forgot_password(self, *, email):
        _StubAuthService.forgot_called_for = email

    def reset_password(self, *, token, new_password):
        _StubAuthService.reset_called_with = {"token": token, "new_password": new_password}


def _make_client(monkeypatch, *, current_user=None):
    monkeypatch.setattr(auth_routes, "AuthService", _StubAuthService)
    app = FastAPI()

    def _fake_get_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_get_db

    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
        # Stub TokenClaims so /auth/logout works without a real bearer header.
        from src.domains.auth.security import TokenClaims

        app.dependency_overrides[current_token_claims] = lambda: TokenClaims(
            sub=str(current_user.id),
            jti="test-jti",
            type="access",
            exp=9999999999,
            iat=0,
        )

    app.include_router(auth_routes.router)
    return TestClient(app)


# ----------------------------------------------------------------------- #


def test_signup_returns_user_and_tokens(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.post(
        "/auth/signup",
        json={
            "email": "newbie@equityai.local",
            "password": "password1234",
            "full_name": "Newbie",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == "newbie@equityai.local"
    assert body["tokens"]["access_token"] == "access-jwt"
    assert body["tokens"]["refresh_token"] == "refresh-jwt"
    assert body["email_verification_required"] is False
    assert _StubAuthService.last_signup_email == "newbie@equityai.local"


def test_login_accepts_email_or_username(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.post(
        "/auth/login",
        json={"identifier": "tester", "password": "password1234"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "access-jwt"
    assert _StubAuthService.last_login_identifier == "tester"


def test_refresh_returns_new_pair(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.post("/auth/refresh", json={"refresh_token": "old-refresh"})
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "new-access"
    assert resp.json()["refresh_token"] == "new-refresh"


def test_logout_blacklists_jti(monkeypatch):
    from tests.conftest import FakeUser

    user = FakeUser()
    client = _make_client(monkeypatch, current_user=user)
    resp = client.post("/auth/logout", json={"refresh_token": "needs-revocation-jwt"})
    # 204 No Content — no body.
    assert resp.status_code == 204
    assert _StubAuthService.logout_called_with is not None
    assert _StubAuthService.logout_called_with["access_token_jti"] == "test-jti"


def test_forgot_password_always_returns_202(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.post(
        "/auth/forgot-password", json={"email": "ghost@equityai.local"}
    )
    assert resp.status_code == 202
    assert _StubAuthService.forgot_called_for == "ghost@equityai.local"


def test_reset_password_consumes_token(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.post(
        "/auth/reset-password",
        json={"token": "abc.token", "new_password": "newPassword1234"},
    )
    assert resp.status_code == 204
    assert _StubAuthService.reset_called_with == {
        "token": "abc.token",
        "new_password": "newPassword1234",
    }


def test_verify_email_consumes_token(monkeypatch):
    client = _make_client(monkeypatch)
    resp = client.post("/auth/verify-email", json={"token": "verify.abc"})
    assert resp.status_code == 200
    assert _StubAuthService.verify_token_consumed == "verify.abc"


def test_me_returns_current_user(monkeypatch):
    from tests.conftest import FakeUser

    user = FakeUser(email="me@equityai.local")
    client = _make_client(monkeypatch, current_user=user)
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@equityai.local"
