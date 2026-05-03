"""Business logic for user profile and KYC operations."""

import hashlib
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.db.models import User

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


class UsersService:
    """Handles user profile, avatar upload, and KYC lifecycle."""

    def __init__(self, db: Session):
        self.db = db
        self.avatar_dir = Path("uploads/avatars")
        self.avatar_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _user_to_dict(user: User) -> dict[str, Any]:
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "address": user.address,
            "pan_card_number": user.pan_card_number,
            "aadhaar_number": user.aadhaar_number,
            "profile_pic_url": user.profile_pic_url,
            "expertise_level": user.expertise_level,
            "risk_tolerance": user.risk_tolerance,
            "investment_horizon": user.investment_horizon,
            "kyc_status": user.kyc_status,
            "kyc_submitted_at": user.kyc_submitted_at.isoformat() if user.kyc_submitted_at else None,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

    def _get_user_or_404(self, user_id: UUID) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def get_user_profile(self, user_id: UUID) -> dict[str, Any]:
        user = self._get_user_or_404(user_id)
        return self._user_to_dict(user)

    def update_user_profile(self, user_id: UUID, update_data: dict[str, Any]) -> dict[str, Any]:
        user = self._get_user_or_404(user_id)

        if "pan_card_number" in update_data and update_data["pan_card_number"]:
            pan = update_data["pan_card_number"].upper()
            if not PAN_REGEX.match(pan):
                raise HTTPException(status_code=400, detail="Invalid PAN format (expected ABCDE1234F)")
            update_data["pan_card_number"] = pan

        if "date_of_birth" in update_data and update_data["date_of_birth"]:
            try:
                update_data["date_of_birth"] = date.fromisoformat(update_data["date_of_birth"])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid date format (expected YYYY-MM-DD)") from exc

        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        try:
            from src.services.cache_service import invalidate_user_profile

            invalidate_user_profile(str(user.id))
        except Exception:
            pass
        return self._user_to_dict(user)

    async def upload_profile_pic(self, user_id: UUID, file: UploadFile) -> dict[str, str]:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        allowed = {".jpg", ".jpeg", ".png", ".webp"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported image type. Allowed: {', '.join(allowed)}")

        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 5MB)")

        user = self._get_user_or_404(user_id)
        file_hash = hashlib.sha256(content).hexdigest()[:12]
        safe_name = f"{user_id}_{file_hash}{ext}"
        file_path = self.avatar_dir / safe_name

        with open(file_path, "wb") as out:
            out.write(content)

        user.profile_pic_url = f"/uploads/avatars/{safe_name}"
        self.db.commit()
        self.db.refresh(user)
        return {"profile_pic_url": user.profile_pic_url}

    def submit_kyc(self, user_id: UUID, pan_card_number: str, aadhaar_number: Optional[str]) -> dict[str, Any]:
        pan = pan_card_number.upper()
        if not PAN_REGEX.match(pan):
            raise HTTPException(status_code=400, detail="Invalid PAN format (expected ABCDE1234F)")

        user = self._get_user_or_404(user_id)
        user.pan_card_number = pan
        if aadhaar_number:
            user.aadhaar_number = aadhaar_number
        user.kyc_status = "pending"
        user.kyc_submitted_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)

        return {
            "kyc_status": user.kyc_status,
            "kyc_submitted_at": user.kyc_submitted_at.isoformat() if user.kyc_submitted_at else None,
            "message": "KYC submitted successfully. Verification in progress.",
        }

    def get_kyc_status(self, user_id: UUID) -> dict[str, Any]:
        user = self._get_user_or_404(user_id)
        return {
            "kyc_status": user.kyc_status,
            "kyc_submitted_at": user.kyc_submitted_at.isoformat() if user.kyc_submitted_at else None,
            "pan_card_number": user.pan_card_number,
        }

    def verify_kyc(self, user_id: UUID) -> dict[str, str]:
        user = self._get_user_or_404(user_id)
        if user.kyc_status not in ("pending", "rejected"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot verify KYC with status '{user.kyc_status}'. Must be pending or rejected.",
            )

        user.kyc_status = "verified"
        self.db.commit()
        self.db.refresh(user)
        return {
            "kyc_status": "verified",
            "message": "KYC verification complete. Your identity has been confirmed.",
        }
