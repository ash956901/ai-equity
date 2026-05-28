"""Chat API routes - query the research agent."""

import logging
import traceback
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.domains.chat.service import ChatService

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
    company_id: Optional[UUID] = Field(
        None, description="Company context for pre-injecting recent news into the agent"
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
def process_query(request: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    """Process a research query through the deep agent orchestrator."""
    print(f"[STAGE 1: ROUTES] Received: user_id={request.user_id}, session_id={request.session_id}, query='{request.query[:50]}...', expertise={request.expertise_level}, upload_id={request.upload_id}")
    
    service = ChatService(db)
    try:
        print(f"[STAGE 2: SERVICE] Calling service.process_query for user_id={request.user_id}")
        
        result = service.process_query(
            user_id=request.user_id,
            query=request.query,
            expertise_level=request.expertise_level,
            session_id=request.session_id,
            upload_id=request.upload_id,
            company_id=request.company_id,
        )
        
        print(f"[STAGE 5: RESPONSE] Got response: session_id={result.get('session_id')}, tokens_used={result.get('tokens_used')}")
        
        # Print response text for debugging
        print(f"[STAGE 5: FINAL_RESPONSE] response = {result.get('response')[:500] if result.get('response') else 'None'}...")
        
        return QueryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Chat query failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{user_id}")
def list_sessions(
    user_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List chat sessions for a user."""
    service = ChatService(db)
    return service.list_sessions(user_id=user_id, limit=limit)
