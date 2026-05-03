"""Pydantic request/response schemas for the auth domain."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    """Accepts either email or username in `identifier`."""

    identifier: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access_token expires


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    expertise_level: str
    risk_tolerance: Optional[str] = None
    investment_horizon: Optional[str] = None
    avatar_url: Optional[str] = None
    theme_preference: Optional[str] = None
    default_chart_range: Optional[str] = None
    sectors_of_interest: Optional[list[str]] = None
    email_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SignupResponse(BaseModel):
    user: CurrentUserResponse
    tokens: TokenPair
    email_verification_required: bool = False
