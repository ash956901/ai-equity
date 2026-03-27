"""Timeline API routes - aggregated event feed."""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Filing, NewsArticle, Company
from src.utils.data_sources import timeline_sources

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/")
def get_timeline(
    user_id: Optional[UUID] = None,
    company_id: Optional[UUID] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get aggregated timeline of filings, news, and signals."""
    events: list[dict[str, Any]] = []
    cutoff = datetime.utcnow() - timedelta(days=90)

    filing_query = db.query(Filing).filter(Filing.filing_date >= cutoff.date())
    if company_id:
        filing_query = filing_query.filter(Filing.company_id == company_id)
    filings = filing_query.order_by(Filing.filing_date.desc()).limit(limit).all()

    for f in filings:
        company = db.query(Company).filter(Company.id == f.company_id).first()
        events.append({
            "id": str(f.id),
            "event_type": "filing",
            "title": f.title,
            "summary": f"{f.filing_type} filed on {f.filing_date.isoformat()}",
            "timestamp": datetime.combine(f.filing_date, datetime.min.time()).isoformat(),
            "company_id": str(f.company_id),
            "company_name": company.name if company else None,
            "metadata": {"filing_type": f.filing_type, "source_url": f.source_url},
            "data_sources": timeline_sources("filing", f.source_url),
        })

    news_query = db.query(NewsArticle).filter(NewsArticle.published_at >= cutoff)
    if company_id:
        news_query = news_query.filter(NewsArticle.company_id == company_id)
    articles = news_query.order_by(NewsArticle.published_at.desc()).limit(limit).all()

    for n in articles:
        company = db.query(Company).filter(Company.id == n.company_id).first() if n.company_id else None
        source_url = n.url if hasattr(n, "url") else None
        events.append({
            "id": str(n.id),
            "event_type": "news",
            "title": n.headline,
            "summary": (n.body or "")[:200],
            "timestamp": n.published_at.isoformat(),
            "company_id": str(n.company_id) if n.company_id else None,
            "company_name": company.name if company else None,
            "metadata": {
                "source": n.source,
                "sentiment": n.sentiment_label,
                "impact": n.impact_level,
                "source_url": source_url,
            },
            "data_sources": timeline_sources("news", source_url),
        })

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events[:limit]
