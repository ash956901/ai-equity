"""File upload API route for document analysis."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User
from src.domains.auth.dependencies import assert_self, get_current_user
from src.domains.chat.upload_service import ChatUploadService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document, persist metadata, and run optional indexing."""
    assert_self(UUID(user_id), current_user)
    service = ChatUploadService(db)
    return await service.upload_document(
        file=file,
        user_id=user_id,
        session_id=session_id,
    )
