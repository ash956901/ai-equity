"""Business logic for document-derived insights."""

from collections import Counter
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models import Company, CompanyInsight, Filing

_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _serialize(row: CompanyInsight, company: Optional[Company], filing: Optional[Filing]) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": str(row.company_id),
        "company_name": company.name if company else None,
        "ticker": (company.ticker_nse or company.ticker_bse) if company else None,
        "sector": company.sector if company else None,
        "insight_type": row.insight_type,
        "title": row.title,
        "detail": row.detail,
        "severity": row.severity,
        "source_quote": row.source_quote,
        "period": row.period,
        "doc_type": row.doc_type,
        "filing_id": str(row.filing_id) if row.filing_id else None,
        "filing_title": filing.title if filing else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class InsightsService:
    def __init__(self, db: Session):
        self.db = db

    def _rank(self, rows: list[CompanyInsight]) -> list[CompanyInsight]:
        return sorted(
            rows,
            key=lambda r: (_SEVERITY_RANK.get(r.severity, 1), -(r.created_at.timestamp() if r.created_at else 0)),
        )

    def company_insights(self, company_id: UUID, limit: int = 50) -> dict[str, Any]:
        company = self.db.query(Company).filter(Company.id == company_id).first()
        rows = (
            self.db.query(CompanyInsight)
            .filter(CompanyInsight.company_id == company_id)
            .all()
        )
        ranked = self._rank(rows)[:limit]

        filings = {
            f.id: f
            for f in self.db.query(Filing).filter(
                Filing.id.in_([r.filing_id for r in ranked if r.filing_id])
            ).all()
        }
        insights = [_serialize(r, company, filings.get(r.filing_id)) for r in ranked]

        return {
            "company_id": str(company_id),
            "company_name": company.name if company else None,
            "digest": {
                "total": len(rows),
                "by_type": dict(Counter(r.insight_type for r in rows)),
                "by_severity": dict(Counter(r.severity for r in rows)),
            },
            "insights": insights,
        }

    def feed(
        self,
        insight_type: Optional[str] = None,
        severity: Optional[str] = None,
        sector: Optional[str] = None,
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        q = self.db.query(CompanyInsight, Company).join(
            Company, Company.id == CompanyInsight.company_id
        )
        if insight_type:
            q = q.filter(CompanyInsight.insight_type == insight_type)
        if severity:
            q = q.filter(CompanyInsight.severity == severity)
        if sector:
            q = q.filter(Company.sector == sector)

        pairs = q.order_by(CompanyInsight.created_at.desc()).limit(limit * 2).all()
        # Rank by severity then recency, then cap.
        pairs.sort(
            key=lambda p: (_SEVERITY_RANK.get(p[0].severity, 1), -(p[0].created_at.timestamp() if p[0].created_at else 0))
        )
        return [_serialize(row, company, None) for row, company in pairs[:limit]]
