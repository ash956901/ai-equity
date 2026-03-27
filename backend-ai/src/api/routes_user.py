"""User profile and KYC API routes."""

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.db.database import get_db
from src.db.models import User

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_DIR = Path("uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


class UserProfileResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    pan_card_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    profile_pic_url: Optional[str] = None
    expertise_level: str = "beginner"
    risk_tolerance: Optional[str] = None
    investment_horizon: Optional[str] = None
    kyc_status: str = "not_started"
    kyc_submitted_at: Optional[str] = None
    is_active: bool = True
    created_at: str
    updated_at: str


class UserProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=15)
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    pan_card_number: Optional[str] = Field(None, max_length=10)
    aadhaar_number: Optional[str] = Field(None, max_length=12)
    expertise_level: Optional[str] = Field(None, max_length=20)
    risk_tolerance: Optional[str] = Field(None, max_length=20)
    investment_horizon: Optional[str] = Field(None, max_length=20)


class KycSubmitRequest(BaseModel):
    pan_card_number: str = Field(..., max_length=10)
    aadhaar_number: Optional[str] = Field(None, max_length=12)


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


@router.get("/{user_id}")
def get_user_profile(user_id: UUID):
    """Fetch user profile."""
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return _user_to_dict(user)
    finally:
        db.close()


@router.put("/{user_id}")
def update_user_profile(user_id: UUID, body: UserProfileUpdate):
    """Update user profile fields."""
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = body.model_dump(exclude_unset=True)

        if "pan_card_number" in update_data and update_data["pan_card_number"]:
            pan = update_data["pan_card_number"].upper()
            if not PAN_REGEX.match(pan):
                raise HTTPException(status_code=400, detail="Invalid PAN format (expected ABCDE1234F)")
            update_data["pan_card_number"] = pan

        if "date_of_birth" in update_data and update_data["date_of_birth"]:
            try:
                update_data["date_of_birth"] = date.fromisoformat(update_data["date_of_birth"])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format (expected YYYY-MM-DD)")

        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return _user_to_dict(user)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/{user_id}/profile-pic")
async def upload_profile_pic(
    user_id: UUID,
    file: UploadFile = File(...),
):
    """Upload a profile picture."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    import os

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported image type. Allowed: {', '.join(allowed)}")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 5MB)")

    file_hash = hashlib.sha256(content).hexdigest()[:12]
    safe_name = f"{user_id}_{file_hash}{ext}"
    file_path = AVATAR_DIR / safe_name

    with open(file_path, "wb") as f:
        f.write(content)

    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.profile_pic_url = f"/uploads/avatars/{safe_name}"
        db.commit()
        db.refresh(user)
        return {"profile_pic_url": user.profile_pic_url}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/{user_id}/kyc/submit")
def submit_kyc(user_id: UUID, body: KycSubmitRequest):
    """Submit KYC verification request."""
    pan = body.pan_card_number.upper()
    if not PAN_REGEX.match(pan):
        raise HTTPException(status_code=400, detail="Invalid PAN format (expected ABCDE1234F)")

    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.pan_card_number = pan
        if body.aadhaar_number:
            user.aadhaar_number = body.aadhaar_number
        user.kyc_status = "pending"
        user.kyc_submitted_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

        return {
            "kyc_status": user.kyc_status,
            "kyc_submitted_at": user.kyc_submitted_at.isoformat(),
            "message": "KYC submitted successfully. Verification in progress.",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{user_id}/kyc/status")
def get_kyc_status(user_id: UUID):
    """Get KYC verification status."""
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "kyc_status": user.kyc_status,
            "kyc_submitted_at": user.kyc_submitted_at.isoformat() if user.kyc_submitted_at else None,
            "pan_card_number": user.pan_card_number,
        }
    finally:
        db.close()


@router.post("/{user_id}/kyc/verify")
def verify_kyc(user_id: UUID):
    """Dummy KYC verification -- auto-approves for demo purposes."""
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.kyc_status not in ("pending", "rejected"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot verify KYC with status '{user.kyc_status}'. Must be pending or rejected.",
            )

        user.kyc_status = "verified"
        db.commit()
        db.refresh(user)
        return {
            "kyc_status": "verified",
            "message": "KYC verification complete. Your identity has been confirmed.",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
