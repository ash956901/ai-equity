"""Chat API routes - query the research agent."""

import logging
import traceback
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import User
from src.domains.auth.dependencies import assert_self, get_current_user
from src.domains.chat.service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class QueryRequest(BaseModel):
    """Chat query request."""

    user_id: UUID = Field(..., description="User UUID")
    session_id: Optional[UUID] = Field(None, description="Existing session ID")
    query: str = Field(..., min_length=1, max_length=2000)
    expertise_level: str = Field(
        default="intermediate",
        description="beginner | intermediate | advanced",
    )
    upload_id: Optional[UUID] = Field(
        None, description="Attached document upload ID for doc analysis"
    )


class QueryResponse(BaseModel):
    """Chat query response."""

    response: str
    sources: list[dict[str, Any]] = []
    visualizations: list[str] = []
    tokens_used: int = 0
    session_id: str
    data_sources: list[dict[str, Any]] = []


@router.post("/query", response_model=QueryResponse)
def process_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """Process a research query through the deep agent orchestrator."""
    assert_self(request.user_id, current_user)
    service = ChatService(db)
    try:
        result = service.process_query(
            user_id=request.user_id,
            query=request.query,
            expertise_level=request.expertise_level or current_user.expertise_level,
            session_id=request.session_id,
            upload_id=request.upload_id,
        )
        return QueryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Chat query failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{user_id}")
def list_sessions(
    user_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List chat sessions for a user."""
    assert_self(user_id, current_user)
    service = ChatService(db)
    return service.list_sessions(user_id=user_id, limit=limit)
