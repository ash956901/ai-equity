"""Auth service: signup / login / refresh / logout / password reset.

Lifts the lid on the User model and the ``security`` helpers; routes stay
thin. Throws ``HTTPException`` for the common failure modes so route
handlers don't need to translate.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import User
from src.domains.auth import email as email_sender
from src.domains.auth import security as sec
from src.domains.auth.schemas import (
    CurrentUserResponse,
    SignupResponse,
    TokenPair,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    #  Signup
    # ------------------------------------------------------------------

    def signup(
        self,
        *,
        email: str,
        username: Optional[str],
        password: str,
        full_name: Optional[str],
    ) -> SignupResponse:
        s = get_settings()
        normalized_email = email.strip().lower()

        existing = (
            self.db.query(User)
            .filter(
                or_(
                    User.email == normalized_email,
                    User.username == (username or "").strip() if username else False,
                )
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email or username already exists",
            )

        user = User(
            email=normalized_email,
            username=(username or "").strip() or None,
            full_name=full_name,
            password_hash=sec.hash_password(password),
            expertise_level="beginner",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        verify_token = sec.issue_one_time_token(
            kind="verify",
            user_id=str(user.id),
            ttl_seconds=s.auth_email_verify_token_hours * 3600,
        )
        try:
            email_sender.send_verify_email(
                to=user.email, token=verify_token, full_name=user.full_name
            )
        except Exception as exc:
            logger.warning("verify email send failed for %s: %s", user.email, exc)

        if s.auth_require_email_verification:
            return SignupResponse(
                user=CurrentUserResponse.model_validate(user),
                tokens=TokenPair(access_token="", refresh_token="", expires_in=0),
                email_verification_required=True,
            )

        tokens = self._mint_token_pair(str(user.id))
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        return SignupResponse(
            user=CurrentUserResponse.model_validate(user),
            tokens=tokens,
            email_verification_required=False,
        )

    # ------------------------------------------------------------------
    #  Login (email or username)
    # ------------------------------------------------------------------

    def login(self, *, identifier: str, password: str) -> TokenPair:
        ident = identifier.strip()
        user = (
            self.db.query(User)
            .filter(or_(User.email == ident.lower(), User.username == ident))
            .first()
        )
        # Always do a constant-time-ish password verify even when user
        # is None so the response time doesn't reveal account existence.
        password_ok = (
            sec.verify_password(password, user.password_hash)
            if user and user.password_hash
            else sec.verify_password(password, "$argon2id$v=19$m=19456,t=2,p=1$placeholder$placeholder")
        )
        if not user or not password_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
            )
        if (
            get_settings().auth_require_email_verification
            and user.email_verified_at is None
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified",
            )

        tokens = self._mint_token_pair(str(user.id))
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        return tokens

    # ------------------------------------------------------------------
    #  Refresh / Logout
    # ------------------------------------------------------------------

    def refresh(self, *, refresh_token: str) -> TokenPair:
        claims = sec.decode_token(refresh_token)
        if not claims or claims.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        # Rotate: must be present in the allow-list, and is removed by `consume_refresh`.
        user_id = sec.consume_refresh(claims.jti)
        if user_id is None or user_id != claims.sub:
            # Possible token replay: nuke any other refresh rotation belonging to this user.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked",
            )
        return self._mint_token_pair(user_id)

    def logout(self, *, access_token_jti: str, access_exp: int, refresh_jti: Optional[str]) -> None:
        sec.blacklist_token(access_token_jti, access_exp)
        if refresh_jti:
            sec.revoke_refresh(refresh_jti)

    # ------------------------------------------------------------------
    #  Email verification
    # ------------------------------------------------------------------

    def verify_email(self, *, token: str) -> CurrentUserResponse:
        user_id = sec.consume_one_time_token(kind="verify", token=token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.email_verified_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return CurrentUserResponse.model_validate(user)

    def resend_verification(self, *, user_id: UUID) -> None:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        s = get_settings()
        token = sec.issue_one_time_token(
            kind="verify",
            user_id=str(user.id),
            ttl_seconds=s.auth_email_verify_token_hours * 3600,
        )
        email_sender.send_verify_email(
            to=user.email, token=token, full_name=user.full_name
        )

    # ------------------------------------------------------------------
    #  Password reset
    # ------------------------------------------------------------------

    def forgot_password(self, *, email: str) -> None:
        normalized = email.strip().lower()
        user = self.db.query(User).filter(User.email == normalized).first()
        # Silently no-op if user is missing (don't leak account existence).
        if not user:
            logger.info("forgot_password: no user for %s (silent)", normalized)
            return
        s = get_settings()
        token = sec.issue_one_time_token(
            kind="reset",
            user_id=str(user.id),
            ttl_seconds=s.auth_password_reset_token_minutes * 60,
        )
        email_sender.send_password_reset_email(
            to=user.email, token=token, full_name=user.full_name
        )

    def reset_password(self, *, token: str, new_password: str) -> None:
        user_id = sec.consume_one_time_token(kind="reset", token=token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.password_hash = sec.hash_password(new_password)
        self.db.commit()

    # ------------------------------------------------------------------
    #  Private
    # ------------------------------------------------------------------

    def _mint_token_pair(self, user_id: str) -> TokenPair:
        s = get_settings()
        access_token, _, access_exp = sec.create_access_token(user_id)
        refresh_token, refresh_jti, refresh_exp = sec.create_refresh_token(user_id)
        sec.remember_refresh(user_id=user_id, jti=refresh_jti, expires_epoch=refresh_exp)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=s.auth_access_token_minutes * 60,
        )
