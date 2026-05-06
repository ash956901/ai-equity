"""Business logic for chat query and session listing."""

import time
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.agents import build_research_agent
from src.db.models import ChatMessage, ChatSession, User, Portfolio
from src.utils.data_sources import DataSource


MAX_AGENT_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0


class ChatService:
    """Encapsulates chat orchestration and persistence logic."""

    def __init__(self, db: Session):
        self.db = db

    def _build_user_message(
        self,
        query: str,
        user_id: UUID,
        expertise_level: str,
        upload_id: Optional[UUID],
        primary_portfolio_id: Optional[UUID],
    ) -> str:
        parts = [query]
        context_lines = [f"user_id={user_id}"]
        if upload_id:
            context_lines.append(f"upload_id={upload_id}")
        if primary_portfolio_id:
            context_lines.append(f"primary_portfolio_id={primary_portfolio_id}")
        context_lines.append(f"expertise_level={expertise_level}")
        parts.append(f"\n\n[Context: {', '.join(context_lines)}]")
        return "".join(parts)

    def process_query(
        self,
        user_id: UUID,
        query: str,
        expertise_level: str,
        session_id: Optional[UUID],
        upload_id: Optional[UUID],
    ) -> dict[str, Any]:
        print(f"[STAGE 2: SERVICE] process_query called: user_id={user_id}, query='{query[:50]}...'")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                email=f"{user_id}@auto.equityai.dev",
                expertise_level=expertise_level,
            )
            self.db.add(user)
            self.db.flush()
            print(f"[STAGE 2a: USER] Created new user: {user_id}")
        else:
            print(f"[STAGE 2a: USER] User exists: {user_id}")

        resolved_session_id = session_id
        if not resolved_session_id:
            session = ChatSession(
                user_id=user_id,
                title=query[:50],
                context_type="general",
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            resolved_session_id = session.id
            print(f"[STAGE 2b: SESSION] Created new session: {resolved_session_id}")
        else:
            session = (
                self.db.query(ChatSession)
                .filter(
                    ChatSession.id == resolved_session_id,
                    ChatSession.user_id == user_id,
                )
                .first()
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            print(f"[STAGE 2b: SESSION] Using existing session: {resolved_session_id}")

        print(f"[STAGE 3: AGENT] Building research agent...")
        agent = build_research_agent()
        print(f"[STAGE 3: AGENT] Research agent built")
        
        primary_portfolio = (
            self.db.query(Portfolio)
            .filter(Portfolio.user_id == user_id, Portfolio.is_primary == True)
            .first()
        )
        primary_portfolio_id = primary_portfolio.id if primary_portfolio else None
        if primary_portfolio_id:
            print(f"[STAGE 3: PORTFOLIO] Primary portfolio: {primary_portfolio_id}")

        user_message = self._build_user_message(
            query=query,
            user_id=user_id,
            expertise_level=expertise_level,
            upload_id=upload_id,
            primary_portfolio_id=primary_portfolio_id,
        )
        
        print(f"[STAGE 3: USER_MESSAGE] Built message (full): {user_message}")

        print(f"[STAGE 4: AGENT_INVOKE] Invoking agent with session_id={resolved_session_id}")
        print(f"[STAGE 4: INPUT_TO_LLM] messages = [{{'role': 'user', 'content': '{user_message}'}}]")
        result: Optional[dict[str, Any]] = None
        last_err = None
        for attempt in range(1, MAX_AGENT_RETRIES + 1):
            try:
                print(f"[STAGE 4: ATTEMPT {attempt}/{MAX_AGENT_RETRIES}] Invoking agent...")
                
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": user_message}]},
                    config={"configurable": {"thread_id": str(resolved_session_id)}},
                )
                
                print(f"[STAGE 4: ATTEMPT {attempt}] Agent invoke succeeded")
                
                last_err = None
                break
            except Exception as invoke_err:
                last_err = invoke_err
                err_msg = str(invoke_err)
                print(f"[STAGE 4: ATTEMPT {attempt}] Agent invoke failed: {err_msg[:200]}")
                
                if "output_parse_failed" in err_msg or "BadRequestError" in type(invoke_err).__name__:
                    print(f"[STAGE 4: RETRY] Retrying after {RETRY_BACKOFF_SECONDS * attempt}s...")
                    if attempt < MAX_AGENT_RETRIES:
                        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                        continue
                raise

        if last_err is not None:
            raise last_err
        if result is None:
            raise RuntimeError("Agent returned no result")

        print(f"[STAGE 4: RESULT_FULL] result keys = {list(result.keys())}")
        
        response_text = result["messages"][-1].content
        print(f"[STAGE 4: LLM_RESPONSE_FULL] response_text = {response_text}")

        tokens_used = 0
        if hasattr(result["messages"][-1], "response_metadata"):
            tokens_used = (
                result["messages"][-1]
                .response_metadata.get("token_usage", {})
                .get("total_tokens", 0)
            )
            print(f"[STAGE 4: TOKENS_USED] tokens_used = {tokens_used}")
            print(f"[STAGE 4: METADATA_FULL] response_metadata = {result['messages'][-1].response_metadata}")

        self.db.add(
            ChatMessage(
                session_id=resolved_session_id,
                role="user",
                content=query,
            )
        )
        self.db.add(
            ChatMessage(
                session_id=resolved_session_id,
                role="assistant",
                content=response_text,
                tokens_used=tokens_used,
            )
        )
        self.db.commit()
        
        print(f"[STAGE 5: DB] Messages saved to DB, session={resolved_session_id}")

        data_sources = [
            DataSource(
                name="EquityAI Research Agent",
                url=f"/chat/sessions/{user_id}",
                data_type="ai_response",
            ).model_dump(),
        ]

        return {
            "response": response_text,
            "tokens_used": tokens_used,
            "session_id": str(resolved_session_id),
            "data_sources": data_sources,
        }

    def list_sessions(self, user_id: UUID, limit: int) -> list[dict[str, Any]]:
        sessions = (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(session.id),
                "title": session.title,
                "context_type": session.context_type,
                "last_message_at": (
                    session.last_message_at.isoformat() if session.last_message_at else None
                ),
                "created_at": session.created_at.isoformat(),
            }
            for session in sessions
        ]
