"""Business logic for timeline aggregation."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models import Company, Filing, NewsArticle, MarketSignal
from src.utils.data_sources import timeline_sources


class TimelineService:
    """Aggregates filing and news events into a single timeline."""

    def __init__(self, db: Session):
        self.db = db

    def get_timeline(
        self,
        user_id: Optional[UUID],
        company_id: Optional[UUID],
        limit: int,
    ) -> list[dict[str, object]]:
        del user_id  # reserved for future personalized events

        events: list[dict[str, object]] = []
        cutoff = datetime.utcnow() - timedelta(days=90)

        filing_query = self.db.query(Filing).filter(Filing.filing_date >= cutoff.date())
        if company_id:
            filing_query = filing_query.filter(Filing.company_id == company_id)
        filings = filing_query.order_by(Filing.filing_date.desc()).limit(limit).all()

        for filing in filings:
            company = self.db.query(Company).filter(Company.id == filing.company_id).first()
            source_url = filing.source_url
            events.append(
                {
                    "id": str(filing.id),
                    "event_type": "filing",
                    "title": filing.title,
                    "summary": f"{filing.filing_type} filed on {filing.filing_date.isoformat()}",
                    "timestamp": datetime.combine(filing.filing_date, datetime.min.time()).isoformat(),
                    "company_id": str(filing.company_id),
                    "company_name": company.name if company else None,
                    "metadata": {"filing_type": filing.filing_type, "source_url": source_url},
                    "data_sources": timeline_sources("filing", source_url),
                }
            )

        news_query = self.db.query(NewsArticle).filter(NewsArticle.published_at >= cutoff)
        if company_id:
            news_query = news_query.filter(NewsArticle.company_id == company_id)
        articles = news_query.order_by(NewsArticle.published_at.desc()).limit(limit).all()

        for article in articles:
            company = (
                self.db.query(Company).filter(Company.id == article.company_id).first()
                if article.company_id
                else None
            )
            source_url = article.source_url
            events.append(
                {
                    "id": str(article.id),
                    "event_type": "news",
                    "title": article.headline,
                    "summary": (article.body or "")[:200],
                    "timestamp": article.published_at.isoformat(),
                    "company_id": str(article.company_id) if article.company_id else None,
                    "company_name": company.name if company else None,
                    "metadata": {
                        "source": article.source,
                        "sentiment": article.sentiment_label,
                        "impact": article.impact_level,
                        "source_url": source_url,
                    },
                    "data_sources": timeline_sources("news", source_url),
                }
            )

        signal_query = self.db.query(MarketSignal).filter(MarketSignal.detected_at >= cutoff)
        if company_id:
            signal_query = signal_query.filter(MarketSignal.company_id == company_id)
        signals = signal_query.order_by(MarketSignal.detected_at.desc()).limit(limit).all()

        for signal in signals:
            company = (
                self.db.query(Company).filter(Company.id == signal.company_id).first()
                if signal.company_id
                else None
            )
            events.append(
                {
                    "id": str(signal.id),
                    "event_type": "signal",
                    "title": signal.title,
                    "summary": signal.summary,
                    "timestamp": signal.detected_at.isoformat(),
                    "company_id": str(signal.company_id) if signal.company_id else None,
                    "company_name": company.name if company else None,
                    "metadata": {
                        "signal_type": signal.signal_type,
                        "impact": signal.impact_level,
                    },
                    "data_sources": [],
                }
            )

        events.sort(key=lambda event: str(event["timestamp"]), reverse=True)
        return events[:limit]
