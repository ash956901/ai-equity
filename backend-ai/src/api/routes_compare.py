"""Company comparison API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents import build_research_agent

router = APIRouter(prefix="/compare", tags=["compare"])


class CompareRequest(BaseModel):
    """Compare companies request."""

    user_id: UUID = Field(..., description="User UUID")
    company_ids: list[UUID] = Field(..., min_length=2, max_length=5)
    query: str = Field(
        default="Compare these companies on growth, profitability, valuation, and risk.",
        max_length=1000,
    )
    expertise_level: str = Field(default="intermediate")


@router.post("/")
def compare_companies(request: CompareRequest) -> dict[str, Any]:
    """Compare 2-5 companies using the deep agent orchestrator."""
    agent = build_research_agent()

    company_ids_str = ", ".join(str(cid) for cid in request.company_ids)
    user_message = (
        f"{request.query}\n\n"
        f"[Context: user_id={request.user_id}, "
        f"company_ids=[{company_ids_str}], "
        f"expertise_level={request.expertise_level}]"
    )

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={
                "configurable": {"thread_id": f"compare-{request.user_id}"}
            },
        )
        response_text = result["messages"][-1].content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "response": response_text,
        "tokens_used": 0,
    }
