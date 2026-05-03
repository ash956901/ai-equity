"""FastAPI dependencies for auth (`get_current_user` etc.).

Token is read from the `Authorization: Bearer <jwt>` header. The resolved
``User`` SQLAlchemy row is cached in Redis under ``user:{user_id}:profile``
for 15 minutes (W6) — invalidated by the users service on profile updates.

The same module exports an ``optional_user`` dep so public endpoints can
still personalise their response when a token is present.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User
from src.domains.auth import security as sec

logger = logging.getLogger(__name__)


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _resolve_user(db: Session, user_id: str) -> Optional[User]:
    # Cached read first
    try:
        from src.services.cache_service import get_user_profile_cached

        cached = get_user_profile_cached(user_id)
        if cached:
            user = User(**cached)
            return user
    except Exception:
        pass
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is not None:
        try:
            from src.services.cache_service import set_user_profile_cached

            set_user_profile_cached(user_id, _user_to_dict(user))
        except Exception:
            pass
    return user


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "expertise_level": user.expertise_level,
        "risk_tolerance": user.risk_tolerance,
        "investment_horizon": user.investment_horizon,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "email_verified_at": getattr(user, "email_verified_at", None),
        "last_login_at": getattr(user, "last_login_at", None),
        "avatar_url": getattr(user, "avatar_url", None),
        "theme_preference": getattr(user, "theme_preference", None),
        "default_chart_range": getattr(user, "default_chart_range", None),
        "sectors_of_interest": getattr(user, "sectors_of_interest", None),
        "password_hash": user.password_hash,
        "kyc_status": user.kyc_status,
    }


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = sec.decode_token(token)
    if not claims or claims.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if sec.is_blacklisted(claims.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = _resolve_user(db, claims.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


def optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_bearer(authorization)
    if not token:
        return None
    claims = sec.decode_token(token)
    if not claims or claims.type != "access" or sec.is_blacklisted(claims.jti):
        return None
    return _resolve_user(db, claims.sub)


def assert_self(target_user_id: UUID, current_user: User) -> None:
    """Raise 403 unless ``target_user_id`` is the authenticated user.

    Used by routes that take ``user_id`` in the path or body to keep the
    existing API contract while preventing cross-account access.
    """
    if target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's resource",
        )


def current_token_claims(
    authorization: Optional[str] = Header(None),
) -> sec.TokenClaims:
    """Return raw claims for endpoints that need them (e.g. logout)."""
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    claims = sec.decode_token(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid token")
    return claims
