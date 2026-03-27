"""Company comparison API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.domains.compare.service import CompareService

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
    service = CompareService()
    try:
        return service.compare(
            user_id=str(request.user_id),
            company_ids=[str(company_id) for company_id in request.company_ids],
            query=request.query,
            expertise_level=request.expertise_level,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
