"""Password hashing + JWT helpers + Redis blacklist & refresh-rotation store.

- Passwords use argon2id (OWASP 2024 recommendation) via ``passlib``.
- Tokens are signed with HS256 (symmetric) — fine for a single backend.
- Refresh tokens are rotated on every use; the old jti is blacklisted.
- A logout blacklists the access-token jti for the remainder of its TTL.

The Redis client is reused from ``src.services.cache_service`` when available;
otherwise an in-memory fallback keeps unit tests green.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from passlib.context import CryptContext

from src.config import get_settings

logger = logging.getLogger(__name__)


pwd_context = CryptContext(
    schemes=["argon2"],
    argon2__memory_cost=19_456,  # ~19 MiB; OWASP min
    argon2__time_cost=2,
    argon2__parallelism=1,
    deprecated="auto",
)


@dataclass(frozen=True)
class TokenClaims:
    sub: str  # user_id
    jti: str
    type: str  # "access" | "refresh"
    exp: int  # epoch seconds
    iat: int


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


# --------------------------------------------------------------------- #
# JWT helpers
# --------------------------------------------------------------------- #


def _settings():
    return get_settings()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(*, user_id: str, token_type: str, expires_in: timedelta) -> tuple[str, str, int]:
    """Encode a JWT and return (token, jti, expires_at_epoch_seconds)."""
    from jose import jwt

    s = _settings()
    jti = secrets.token_urlsafe(16)
    iat = int(_now().timestamp())
    exp_dt = _now() + expires_in
    exp = int(exp_dt.timestamp())
    claims = {
        "sub": user_id,
        "jti": jti,
        "type": token_type,
        "iat": iat,
        "exp": exp,
    }
    token = jwt.encode(claims, s.auth_jwt_secret, algorithm=s.auth_jwt_algorithm)
    return token, jti, exp


def create_access_token(user_id: str) -> tuple[str, str, int]:
    s = _settings()
    return _create_token(
        user_id=user_id,
        token_type="access",
        expires_in=timedelta(minutes=s.auth_access_token_minutes),
    )


def create_refresh_token(user_id: str) -> tuple[str, str, int]:
    s = _settings()
    return _create_token(
        user_id=user_id,
        token_type="refresh",
        expires_in=timedelta(days=s.auth_refresh_token_days),
    )


def decode_token(token: str) -> Optional[TokenClaims]:
    """Return claims if signature + expiry are valid, else None."""
    from jose import JWTError, jwt

    s = _settings()
    try:
        payload = jwt.decode(token, s.auth_jwt_secret, algorithms=[s.auth_jwt_algorithm])
    except JWTError as exc:
        logger.debug("jwt decode failed: %s", exc)
        return None
    try:
        return TokenClaims(
            sub=str(payload["sub"]),
            jti=str(payload["jti"]),
            type=str(payload.get("type", "access")),
            exp=int(payload["exp"]),
            iat=int(payload.get("iat", 0)),
        )
    except (KeyError, ValueError, TypeError):
        return None


# --------------------------------------------------------------------- #
# Redis blacklist + refresh allow-list
# --------------------------------------------------------------------- #


_FALLBACK_STORE: dict[str, tuple[str, float]] = {}  # key -> (value, expires_at_epoch)


def _redis_client():
    """Return a Redis client or None. Imported lazily so tests work without Redis."""
    try:
        import redis  # type: ignore

        from src.config import get_settings

        url = get_settings().redis_url or "redis://localhost:6379/0"
        client = redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5)
        client.ping()
        return client
    except Exception as exc:
        logger.debug("Redis unavailable, using in-memory blacklist fallback: %s", exc)
        return None


def _kv_set(key: str, value: str, ttl_seconds: int) -> None:
    client = _redis_client()
    if client is not None:
        try:
            client.set(key, value, ex=max(ttl_seconds, 1))
            return
        except Exception as exc:
            logger.debug("redis set failed: %s", exc)
    _FALLBACK_STORE[key] = (value, _now().timestamp() + ttl_seconds)


def _kv_get(key: str) -> Optional[str]:
    client = _redis_client()
    if client is not None:
        try:
            val = client.get(key)
            return val.decode("utf-8") if isinstance(val, (bytes, bytearray)) else val
        except Exception as exc:
            logger.debug("redis get failed: %s", exc)
    pair = _FALLBACK_STORE.get(key)
    if not pair:
        return None
    value, exp = pair
    if exp < _now().timestamp():
        _FALLBACK_STORE.pop(key, None)
        return None
    return value


def _kv_delete(key: str) -> None:
    client = _redis_client()
    if client is not None:
        try:
            client.delete(key)
        except Exception as exc:
            logger.debug("redis del failed: %s", exc)
    _FALLBACK_STORE.pop(key, None)


def blacklist_token(jti: str, expires_epoch: int) -> None:
    """Mark a JWT jti as revoked until its natural expiry."""
    ttl = max(int(expires_epoch - _now().timestamp()), 1)
    _kv_set(f"auth:blacklist:{jti}", "1", ttl_seconds=ttl)


def is_blacklisted(jti: str) -> bool:
    return _kv_get(f"auth:blacklist:{jti}") is not None


def remember_refresh(user_id: str, jti: str, expires_epoch: int) -> None:
    """Allow-list a refresh token. We accept a refresh only if its jti is here."""
    ttl = max(int(expires_epoch - _now().timestamp()), 1)
    _kv_set(f"auth:refresh:{jti}", user_id, ttl_seconds=ttl)


def consume_refresh(jti: str) -> Optional[str]:
    """Return the user_id this refresh belongs to, then DELETE it (rotation)."""
    user_id = _kv_get(f"auth:refresh:{jti}")
    if user_id is None:
        return None
    _kv_delete(f"auth:refresh:{jti}")
    return user_id


def revoke_refresh(jti: str) -> None:
    _kv_delete(f"auth:refresh:{jti}")


# --------------------------------------------------------------------- #
# Single-use email-verification + password-reset tokens
# --------------------------------------------------------------------- #


def issue_one_time_token(*, kind: str, user_id: str, ttl_seconds: int) -> str:
    """Mint an opaque token bound to a user_id and a `kind`. Stored in Redis."""
    token = secrets.token_urlsafe(32)
    _kv_set(f"auth:onetime:{kind}:{token}", user_id, ttl_seconds=ttl_seconds)
    return token


def consume_one_time_token(*, kind: str, token: str) -> Optional[str]:
    """Return user_id and delete the token, or None if invalid/expired."""
    user_id = _kv_get(f"auth:onetime:{kind}:{token}")
    if user_id is None:
        return None
    _kv_delete(f"auth:onetime:{kind}:{token}")
    return user_id


def new_request_id() -> str:
    """Helper for log correlation when no FastAPI request_id middleware sits in front."""
    return str(uuid.uuid4())
