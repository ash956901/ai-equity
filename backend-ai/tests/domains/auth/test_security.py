"""Pure-unit tests for src.domains.auth.security helpers."""

from __future__ import annotations

import time
from datetime import timedelta

from src.domains.auth import security as sec


def test_password_hash_and_verify_roundtrip():
    pw = "correct horse battery staple"
    hashed = sec.hash_password(pw)
    assert hashed != pw
    assert hashed.startswith("$argon2")
    assert sec.verify_password(pw, hashed) is True
    assert sec.verify_password("wrong password", hashed) is False


def test_verify_password_handles_garbage_hash():
    # Should never raise even if the stored hash is bogus.
    assert sec.verify_password("anything", "not-a-real-hash") is False
    assert sec.verify_password("anything", "") is False


def test_create_and_decode_access_token():
    user_id = "11111111-1111-1111-1111-111111111111"
    token, jti, exp = sec.create_access_token(user_id)
    assert isinstance(token, str) and token.count(".") == 2
    assert isinstance(jti, str) and len(jti) >= 16
    assert exp > int(time.time())

    claims = sec.decode_token(token)
    assert claims is not None
    assert claims.sub == user_id
    assert claims.jti == jti
    assert claims.type == "access"


def test_decode_rejects_garbage():
    assert sec.decode_token("nonsense") is None
    assert sec.decode_token("") is None


def test_blacklist_round_trip():
    user_id = "22222222-2222-2222-2222-222222222222"
    _, jti, exp = sec.create_access_token(user_id)
    assert sec.is_blacklisted(jti) is False
    sec.blacklist_token(jti, exp)
    assert sec.is_blacklisted(jti) is True


def test_refresh_rotation_consume_returns_user_id():
    user_id = "33333333-3333-3333-3333-333333333333"
    _, jti, exp = sec.create_refresh_token(user_id)
    sec.remember_refresh(user_id=user_id, jti=jti, expires_epoch=exp)
    assert sec.consume_refresh(jti) == user_id
    # Second consumption fails — it's single-use.
    assert sec.consume_refresh(jti) is None


def test_one_time_token_round_trip():
    user_id = "44444444-4444-4444-4444-444444444444"
    token = sec.issue_one_time_token(kind="verify", user_id=user_id, ttl_seconds=60)
    assert sec.consume_one_time_token(kind="verify", token=token) == user_id
    # Single-use.
    assert sec.consume_one_time_token(kind="verify", token=token) is None
    # Wrong kind doesn't match.
    fresh = sec.issue_one_time_token(kind="reset", user_id=user_id, ttl_seconds=60)
    assert sec.consume_one_time_token(kind="verify", token=fresh) is None
    assert sec.consume_one_time_token(kind="reset", token=fresh) == user_id


def test_token_claims_dataclass_immutable():
    """TokenClaims is frozen so callers can't accidentally mutate jti, etc."""
    user_id = "55555555-5555-5555-5555-555555555555"
    _, jti, _ = sec.create_access_token(user_id)
    decoded = sec.decode_token(_jwt_for(user_id, jti))
    if decoded is None:
        # Edge case: re-encode and try again. Our helper should always
        # produce a valid token.
        token, jti, _ = sec.create_access_token(user_id)
        decoded = sec.decode_token(token)
    assert decoded is not None
    try:
        decoded.jti = "tampered"  # type: ignore[misc]
    except Exception:
        return  # Frozen dataclass raises on assignment — pass.
    raise AssertionError("TokenClaims should be frozen")


def _jwt_for(user_id: str, _jti: str) -> str:
    """Helper: just mint a fresh access token. Avoids depending on jose
    encode internals from the test."""
    token, _, _ = sec.create_access_token(user_id)
    return token
