"""Business logic for timeline aggregation."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models import Company, Filing, FilingSummary, NewsArticle
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

        filing_query = (
            self.db.query(Filing, FilingSummary)
            .outerjoin(FilingSummary, FilingSummary.filing_id == Filing.id)
            .filter(Filing.filing_date >= cutoff.date())
        )
        if company_id:
            filing_query = filing_query.filter(Filing.company_id == company_id)
        filings = filing_query.order_by(Filing.filing_date.desc()).limit(limit).all()

        for filing, summary in filings:
            company = self.db.query(Company).filter(Company.id == filing.company_id).first()
            source_url = filing.source_url
            # Prefer the AI one-liner; fall back to the static template only
            # when the offline summarizer hasn't run for this filing yet.
            if summary and summary.summary_one_liner:
                summary_text = summary.summary_one_liner
                ev_type = summary.event_type or "filing"
                materiality = (
                    float(summary.materiality_score)
                    if summary.materiality_score is not None
                    else None
                )
                sentiment = summary.sentiment
                affected_dim = summary.affected_dimension
            else:
                summary_text = (
                    f"{filing.filing_type} filed on {filing.filing_date.isoformat()}"
                )
                ev_type = "filing"
                materiality = None
                sentiment = None
                affected_dim = None

            events.append(
                {
                    "id": str(filing.id),
                    "event_type": ev_type,
                    "title": filing.title,
                    "summary": summary_text,
                    "timestamp": datetime.combine(
                        filing.filing_date, datetime.min.time()
                    ).isoformat(),
                    "company_id": str(filing.company_id),
                    "company_name": company.name if company else None,
                    "metadata": {
                        "filing_type": filing.filing_type,
                        "source_url": source_url,
                        "materiality_score": materiality,
                        "sentiment": sentiment,
                        "affected_dimension": affected_dim,
                    },
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

        events.sort(key=lambda event: str(event["timestamp"]), reverse=True)
        return events[:limit]
