"""Causal intelligence endpoints — surfaces the Causal Detective's insights via REST."""

import logging
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import CausalChain, ClassifiedNews, Company, Portfolio
from src.services.causal_service import CausalService

router = APIRouter(prefix="/causal", tags=["causal"])


# ── Market-wide signal feed ──────────────────────────────────────────────────

@router.get("/market")
def get_market_causal(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return commodity trends, geo events, news impacts, and all active causal chains."""
    service = CausalService(db)

    commodity_changes = service.get_commodity_changes(days=7)
    events = service.get_recent_significant_events(hours=48, min_confidence=0.6)
    news = (
        db.query(ClassifiedNews)
        .filter(ClassifiedNews.impact_direction.isnot(None))
        .order_by(ClassifiedNews.created_at.desc())
        .limit(15)
        .all()
    )
    chains = db.query(CausalChain).filter(CausalChain.is_active.is_(True)).all()

    chain_list = []
    for c in chains:
        change_pct = commodity_changes.get(c.hop1_target, {}).get("change_pct", 0.0) or 0.0
        chain_list.append({
            "id": str(c.id),
            "name": c.name,
            "trigger_type": c.trigger_type,
            "trigger_value": c.trigger_value,
            "hop1_target": c.hop1_target,
            "hop1_relationship": c.hop1_relationship,
            "hop2_target": c.hop2_target,
            "hop2_relationship": c.hop2_relationship,
            "hop3_target": c.hop3_target,
            "hop3_relationship": c.hop3_relationship,
            "confidence": c.confidence,
            "current_commodity_change_pct": change_pct,
        })

    return {
        "commodity_trends": commodity_changes,
        "geopolitical_events": [
            {
                "title": e.title,
                "country": e.country or "",
                "category": e.category or "",
                "confidence": e.confidence or 0.0,
                "goldstein_scale": e.goldstein_scale,
                "date": e.event_date.isoformat() if e.event_date else None,
            }
            for e in events
        ],
        "news_impacts": [
            {
                "title": n.title,
                "source": n.source,
                "commodity": n.commodity,
                "sector": n.sector,
                "impact_direction": n.impact_direction,
                "classification_confidence": n.classification_confidence,
                "published_at": n.published_at.isoformat() if n.published_at else None,
            }
            for n in news
        ],
        "causal_chains": chain_list,
    }


# ── Portfolio-specific causal impacts ────────────────────────────────────────

@router.get("/portfolio")
def get_portfolio_causal(user_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return commodity-driven impacts on the user's primary portfolio holdings."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id, Portfolio.is_primary.is_(True))
        .first()
    ) or (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id)
        .first()
    )

    if not portfolio:
        return {"portfolio_id": None, "patterns": []}

    service = CausalService(db)
    try:
        patterns = service.analyze_portfolio(portfolio.id)
    except Exception as exc:
        logger.warning("analyze_portfolio failed for %s: %s", portfolio.id, exc)
        patterns = []
    return {"portfolio_id": str(portfolio.id), "patterns": patterns}


# ── Company-specific causal exposures ────────────────────────────────────────

@router.get("/company/{company_id}")
def get_company_causal(company_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return sector-based commodity exposures and news impacts for a company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    service = CausalService(db)
    commodity_changes = service.get_commodity_changes(days=7)
    exposures = service.get_sector_exposure(company.sector or "")

    news = (
        db.query(ClassifiedNews)
        .filter(
            ClassifiedNews.sector == company.sector,
            ClassifiedNews.impact_direction.isnot(None),
        )
        .order_by(ClassifiedNews.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "company_id": str(company.id),
        "company_name": company.name,
        "sector": company.sector or "Unknown",
        "exposures": [
            {
                "commodity": e.commodity,
                "dependency_type": e.dependency_type,
                "impact_direction": e.impact_direction,
                "impact_magnitude": e.impact_magnitude,
                "affected_companies": e.affected_companies or [],
                "current_change_pct": commodity_changes.get(e.commodity, {}).get("change_pct", 0.0) or 0.0,
                "commodity_direction": commodity_changes.get(e.commodity, {}).get("direction", "stable") or "stable",
            }
            for e in exposures
        ],
        "news_impacts": [
            {
                "title": n.title,
                "source": n.source,
                "commodity": n.commodity,
                "impact_direction": n.impact_direction,
                "classification_confidence": n.classification_confidence,
            }
            for n in news
        ],
    }


# ── LLM deep-dive analysis ───────────────────────────────────────────────────

class LLMAnalyzeRequest(BaseModel):
    trigger: str
    company_id: Optional[str] = None


@router.post("/llm-analyze")
def llm_analyze(body: LLMAnalyzeRequest) -> dict[str, Any]:
    """Run LLM-powered causal chain analysis for a custom trigger string."""
    try:
        from src.agents.tools.causal_tools import analyze_causal_chain_with_llm
        result = analyze_causal_chain_with_llm(body.trigger)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM analysis failed: {exc}") from exc
