"""Auth service — OTP generation, JWT creation, session management."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import OTP, User, UserSession

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    # ── OTP ──────────────────────────────────────────────────────────────

    def send_otp(self, email: str, purpose: str) -> int:
        """Generate and store an OTP. Returns expiry in seconds.

        Raises ValueError on rate-limit / too many attempts.
        """
        now = _now_utc()
        hour_ago = now - timedelta(hours=1)

        recent_count = (
            self.db.query(OTP)
            .filter(
                OTP.email == email,
                OTP.created_at >= hour_ago,
            )
            .count()
        )

        if recent_count >= self.settings.otp_rate_limit_per_hour:
            raise ValueError("Too many OTP requests. Please try again later.")

        # Invalidate any previous unused OTPs for this email+purpose
        (
            self.db.query(OTP)
            .filter(
                OTP.email == email,
                OTP.purpose == purpose,
                OTP.is_used == False,
            )
            .update({"is_used": True})
        )
        self.db.flush()

        code = "".join(secrets.choice("0123456789") for _ in range(self.settings.otp_length))
        expires_at = now + timedelta(minutes=self.settings.otp_expiry_minutes)

        otp = OTP(
            email=email,
            otp_code=code,
            purpose=purpose,
            expires_at=expires_at,
            is_used=False,
            attempts=0,
        )
        self.db.add(otp)
        self.db.commit()

        return self.settings.otp_expiry_minutes * 60

    def verify_otp(self, email: str, code: str, purpose: str) -> OTP:
        """Verify an OTP code. Returns the OTP record on success.

        Raises ValueError on failure.
        """
        now = _now_utc()

        otp = (
            self.db.query(OTP)
            .filter(
                OTP.email == email,
                OTP.purpose == purpose,
                OTP.is_used == False,
            )
            .order_by(OTP.created_at.desc())
            .first()
        )

        if not otp:
            raise ValueError("No valid OTP found. Please request a new one.")

        if otp.expires_at.replace(tzinfo=timezone.utc) < now:
            otp.is_used = True
            self.db.commit()
            raise ValueError("OTP expired. Please request a new one.")

        if otp.attempts >= self.settings.otp_max_attempts:
            otp.is_used = True
            self.db.commit()
            raise ValueError("Too many attempts. Please request a new OTP.")

        otp.attempts += 1
        self.db.commit()

        if not secrets.compare_digest(otp.otp_code, code):
            raise ValueError("Invalid OTP. Please try again.")

        otp.is_used = True
        self.db.commit()
        return otp

    # ── User ─────────────────────────────────────────────────────────────

    def get_or_create_user(self, email: str, purpose: str, full_name: str | None = None) -> tuple[User, bool]:
        """Get existing user or create new one. Returns (user, is_new)."""
        user = self.db.query(User).filter(User.email == email).first()

        if user:
            return user, False

        username = email.split("@")[0]

        existing_username = self.db.query(User).filter(User.username == username).first()
        if existing_username:
            username = f"{username}_{secrets.token_hex(3)}"

        user = User(
            email=email,
            username=username,
            full_name=full_name,
            is_active=True,
            expertise_level="beginner",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user, True

    # ── JWT tokens ───────────────────────────────────────────────────────

    def _create_token(self, user: User, token_type: str, jti: str) -> str:
        now = _now_utc()

        if token_type == "access":
            exp = now + timedelta(minutes=self.settings.jwt_access_token_expire_minutes)
        else:
            exp = now + timedelta(days=self.settings.jwt_refresh_token_expire_days)

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "jti": jti,
            "type": token_type,
            "iat": now,
            "exp": exp,
        }

        return jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
        )

    def create_session(self, user: User, user_agent: str | None = None, ip_address: str | None = None) -> dict:
        """Create a new session with access + refresh tokens.

        Returns dict with access_token, refresh_token, refresh_expires.
        """
        now = _now_utc()
        access_jti = uuid.uuid4().hex
        refresh_jti = uuid.uuid4().hex
        refresh_expires = now + timedelta(days=self.settings.jwt_refresh_token_expire_days)

        session = UserSession(
            user_id=user.id,
            access_token_jti=access_jti,
            refresh_token_jti=refresh_jti,
            user_agent=user_agent,
            ip_address=ip_address,
            is_revoked=False,
            created_at=now,
            expires_at=refresh_expires,
        )
        self.db.add(session)
        self.db.commit()

        access_token = self._create_token(user, "access", access_jti)
        refresh_token = self._create_token(user, "refresh", refresh_jti)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "refresh_expires": int(refresh_expires.timestamp()),
        }

    def refresh_session(self, refresh_token: str, user_agent: str | None = None, ip_address: str | None = None) -> dict:
        """Rotate refresh token and issue new access token.

        Returns dict with new access_token, refresh_token, refresh_expires.
        Raises ValueError on invalid/expired/revoked token.
        """
        try:
            payload = jwt.decode(
                refresh_token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")

        jti = payload.get("jti")
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not jti or not user_id or token_type != "refresh":
            raise ValueError("Invalid refresh token payload")

        session = (
            self.db.query(UserSession)
            .filter(
                UserSession.refresh_token_jti == jti,
                UserSession.is_revoked == False,
            )
            .first()
        )

        if not session:
            raise ValueError("Session revoked")

        if session.expires_at.replace(tzinfo=timezone.utc) < _now_utc():
            raise ValueError("Session expired")

        user = self.db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        session.is_revoked = True
        self.db.commit()

        return self.create_session(user, user_agent, ip_address)

    def revoke_session(self, refresh_jti: str) -> None:
        """Revoke a session by its refresh token JTI."""
        session = (
            self.db.query(UserSession)
            .filter(UserSession.refresh_token_jti == refresh_jti)
            .first()
        )
        if session:
            session.is_revoked = True
            self.db.commit()

    def revoke_all_sessions(self, user_id: uuid.UUID) -> None:
        """Revoke all sessions for a user."""
        (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_revoked == False)
            .update({"is_revoked": True})
        )
        self.db.commit()
