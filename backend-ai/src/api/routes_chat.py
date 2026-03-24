"""Chat API routes - query the research agent."""

import logging
import time
import traceback
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents import build_research_agent
from src.db.database import get_db
from src.db.models import ChatMessage, ChatSession, User

logger = logging.getLogger(__name__)

MAX_AGENT_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0

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


def _build_user_message(request: QueryRequest) -> str:
    """Compose the user message with optional context metadata."""
    parts = [request.query]
    context_lines = [f"user_id={request.user_id}"]
    if request.upload_id:
        context_lines.append(f"upload_id={request.upload_id}")
    context_lines.append(f"expertise_level={request.expertise_level}")
    parts.append(f"\n\n[Context: {', '.join(context_lines)}]")
    return "".join(parts)


@router.post("/query", response_model=QueryResponse)
def process_query(request: QueryRequest) -> QueryResponse:
    """Process a research query through the deep agent orchestrator."""
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            user = User(
                id=request.user_id,
                email=f"{request.user_id}@auto.equityai.dev",
                expertise_level=request.expertise_level,
            )
            db.add(user)
            db.flush()

        session_id = request.session_id
        if not session_id:
            session = ChatSession(
                user_id=request.user_id,
                title=request.query[:50],
                context_type="general",
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.id
        else:
            session = (
                db.query(ChatSession)
                .filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == request.user_id,
                )
                .first()
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

        agent = build_research_agent()
        user_message = _build_user_message(request)

        last_err = None
        for attempt in range(1, MAX_AGENT_RETRIES + 1):
            try:
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": user_message}]},
                    config={"configurable": {"thread_id": str(session_id)}},
                )
                last_err = None
                break
            except Exception as invoke_err:
                last_err = invoke_err
                err_msg = str(invoke_err)
                if "output_parse_failed" in err_msg or "BadRequestError" in type(invoke_err).__name__:
                    logger.warning(
                        "Agent invocation attempt %d/%d failed (retryable): %s",
                        attempt, MAX_AGENT_RETRIES, err_msg[:200],
                    )
                    if attempt < MAX_AGENT_RETRIES:
                        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                        continue
                raise

        if last_err is not None:
            raise last_err

        response_text = result["messages"][-1].content
        tokens_used = 0
        if hasattr(result["messages"][-1], "response_metadata"):
            tokens_used = (
                result["messages"][-1]
                .response_metadata.get("token_usage", {})
                .get("total_tokens", 0)
            )

        db.add(
            ChatMessage(
                session_id=session_id,
                role="user",
                content=request.query,
            )
        )
        db.add(
            ChatMessage(
                session_id=session_id,
                role="assistant",
                content=response_text,
                tokens_used=tokens_used,
            )
        )
        db.commit()

        from src.utils.data_sources import DataSource
        data_sources = [
            DataSource(
                name="EquityAI Research Agent",
                url=f"/chat/sessions/{request.user_id}",
                data_type="ai_response",
            ).model_dump(),
        ]

        return QueryResponse(
            response=response_text,
            tokens_used=tokens_used,
            session_id=str(session_id),
            data_sources=data_sources,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Chat query failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/sessions/{user_id}")
def list_sessions(user_id: UUID, limit: int = 20):
    """List chat sessions for a user."""
    db = next(get_db())
    try:
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "context_type": s.context_type,
                "last_message_at": (
                    s.last_message_at.isoformat() if s.last_message_at else None
                ),
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ]
    finally:
        db.close()
