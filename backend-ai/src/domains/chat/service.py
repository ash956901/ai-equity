"""Business logic for chat query and session listing."""

import time
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.agents.router import route_query, QueryRoute
from src.agents.handlers.comparison_handler import handle_comparison
from src.agents.handlers.portfolio_handler import handle_portfolio
from src.agents.handlers.causal_handler import handle_causal
from src.agents.handlers.general_handler import handle_analysis, handle_news, handle_general
from src.db.models import ChatMessage, ChatSession, User, Portfolio
from src.utils.data_sources import DataSource


class ChatService:
    """Encapsulates chat orchestration and persistence logic."""

    def __init__(self, db: Session):
        self.db = db

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

        route = route_query(query)
        print(f"[ROUTER] Query classified as: {route}")
        
        start_time = time.time()
        
        if route == QueryRoute.COMPARE:
            response_text = handle_comparison(query, self.db, str(user_id), expertise_level)
        elif route == QueryRoute.PORTFOLIO:
            response_text = handle_portfolio(query, self.db, str(user_id), expertise_level)
        elif route == QueryRoute.CAUSAL:
            response_text = handle_causal(query, self.db, str(user_id), expertise_level)
        elif route == QueryRoute.ANALYZE:
            response_text = handle_analysis(query, self.db, str(user_id), expertise_level)
        elif route == QueryRoute.NEWS:
            response_text = handle_news(query, self.db, str(user_id), expertise_level)
        else:
            response_text = handle_general(query, self.db, str(user_id), expertise_level)

        tokens_used = 0 # Handlers natively abstract tokens
        duration = time.time() - start_time
        print(f"[STAGE 4: LLM_RESPONSE] Response generated in {duration:.2f}s: {response_text[:100]}...")

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
