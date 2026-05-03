"""Auth API: signup / login / refresh / logout / verify / forgot / reset / me."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User
from src.domains.auth.dependencies import (
    current_token_claims,
    get_current_user,
)
from src.domains.auth.schemas import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    TokenPair,
    VerifyEmailRequest,
)
from src.domains.auth.service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------- #
# Optional rate limiting via slowapi.                                    #
# ---------------------------------------------------------------------- #

_limiter = None
try:
    from slowapi import Limiter  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore

    _limiter = Limiter(key_func=get_remote_address)
except ImportError:  # pragma: no cover
    _limiter = None


def _rate_limit(rate_str: str):
    """Decorator that's a no-op when slowapi is missing."""
    if _limiter is None:
        def deco(fn):
            return fn
        return deco
    return _limiter.limit(rate_str)


def _rate_value(name: str, default: str) -> str:
    from src.config import get_settings

    return getattr(get_settings(), name, default)


# ---------------------------------------------------------------------- #
#  Endpoints                                                             #
# ---------------------------------------------------------------------- #


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
@_rate_limit(_rate_value("auth_signup_rate_limit", "3/minute"))
def signup(
    request: Request,
    body: SignupRequest,
    db: Session = Depends(get_db),
):
    return AuthService(db).signup(
        email=body.email,
        username=body.username,
        password=body.password,
        full_name=body.full_name,
    )


@router.post("/login", response_model=TokenPair)
@_rate_limit(_rate_value("auth_login_rate_limit", "5/minute"))
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    return AuthService(db).login(identifier=body.identifier, password=body.password)


@router.post("/refresh", response_model=TokenPair)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    return AuthService(db).refresh(refresh_token=body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    refresh_token: Optional[str] = Body(default=None, embed=True),
    claims = Depends(current_token_claims),
    db: Session = Depends(get_db),
):
    """Logout the current access token (and optionally the refresh)."""
    refresh_jti = None
    if refresh_token:
        from src.domains.auth import security as sec

        decoded = sec.decode_token(refresh_token)
        if decoded and decoded.type == "refresh":
            refresh_jti = decoded.jti
    AuthService(db).logout(
        access_token_jti=claims.jti,
        access_exp=claims.exp,
        refresh_jti=refresh_jti,
    )
    return None


@router.post("/verify-email", response_model=CurrentUserResponse)
def verify_email(
    body: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    return AuthService(db).verify_email(token=body.token)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService(db).resend_verification(user_id=user.id)
    return None


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@_rate_limit(_rate_value("auth_forgot_rate_limit", "3/minute"))
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    AuthService(db).forgot_password(email=body.email)
    # Always 202 — never reveal whether the email exists.
    return {"status": "accepted"}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    AuthService(db).reset_password(token=body.token, new_password=body.new_password)
    return None


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)):
    return CurrentUserResponse.model_validate(user)
