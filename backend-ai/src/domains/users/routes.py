"""User profile and KYC API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.domains.users.service import UsersService

router = APIRouter(prefix="/users", tags=["users"])


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


@router.get("/{user_id}")
def get_user_profile(user_id: UUID, db: Session = Depends(get_db)):
    """Fetch user profile."""
    service = UsersService(db)
    return service.get_user_profile(user_id)


@router.put("/{user_id}")
def update_user_profile(
    user_id: UUID,
    body: UserProfileUpdate,
    db: Session = Depends(get_db),
):
    """Update user profile fields."""
    service = UsersService(db)
    update_data = body.model_dump(exclude_unset=True)
    return service.update_user_profile(user_id=user_id, update_data=update_data)


@router.post("/{user_id}/profile-pic")
async def upload_profile_pic(
    user_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a profile picture."""
    service = UsersService(db)
    return await service.upload_profile_pic(user_id=user_id, file=file)


@router.post("/{user_id}/kyc/submit")
def submit_kyc(
    user_id: UUID,
    body: KycSubmitRequest,
    db: Session = Depends(get_db),
):
    """Submit KYC verification request."""
    service = UsersService(db)
    return service.submit_kyc(
        user_id=user_id,
        pan_card_number=body.pan_card_number,
        aadhaar_number=body.aadhaar_number,
    )


@router.get("/{user_id}/kyc/status")
def get_kyc_status(user_id: UUID, db: Session = Depends(get_db)):
    """Get KYC verification status."""
    service = UsersService(db)
    return service.get_kyc_status(user_id)


@router.post("/{user_id}/kyc/verify")
def verify_kyc(user_id: UUID, db: Session = Depends(get_db)):
    """Dummy KYC verification -- auto-approves for demo purposes."""
    service = UsersService(db)
    return service.verify_kyc(user_id)
