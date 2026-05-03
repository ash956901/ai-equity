"""Personalised home dashboard route."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User
from src.domains.auth.dependencies import get_current_user
from src.domains.home.service import HomeService

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/personalized")
def get_personalized(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return HomeService(db).get_personalized(user)
