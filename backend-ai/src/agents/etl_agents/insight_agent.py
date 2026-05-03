"""Insight Discovery Agent.

Composes daily insight cards by joining:

- ``company_themes`` (Theme Tagging Agent output)
- ``events`` (Event Extraction Agent output)
- ``commodity_series`` deltas + ``sector_commodity_links``
- ``social_posts`` aggregate sentiment

For each candidate pattern it picks the appropriate prompt template (causal,
ripple, sentiment, event), optionally calls the LLM, and persists an
``Insight`` row plus ``InsightEvidence`` provenance.

The agent is built so that Phase-1 deployments without an LLM key still
generate skeletal insight cards from the deterministic rule layer.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.agents.prompts.insights import (
    build_causal_cross_industry_messages,
    build_event_catalyst_messages,
    build_sentiment_driven_messages,
    build_supply_chain_ripple_messages,
)
from src.db.database import SessionLocal
from src.db.models import (
    CommoditySeries,
    Company,
    CompanyTheme,
    Event,
    Insight,
    InsightEvidence,
    NewsArticle,
    SectorCommodityLink,
    SocialPost,
)
from src.etl.confidence import aggregate_confidence, to_decimal
from src.etl.macro_ingest import get_recent_series_change

logger = logging.getLogger(__name__)


def _safe_llm_invoke(messages) -> Optional[str]:
    """Call the configured LLM if available; otherwise return None."""
    try:
        from src.config import get_settings
        from src.llm import get_llm

        settings = get_settings()
        if settings.llm_provider == "openai" and not settings.openai_api_key:
            return None
        if settings.llm_provider == "groq" and not settings.groq_api_key:
            return None
        if settings.llm_provider == "deepseek" and not settings.deepseek_api_key:
            return None
        llm = get_llm(temperature=0.2)
        resp = llm.invoke(messages)
        return getattr(resp, "content", "") or ""
    except Exception as exc:
        logger.debug("InsightAgent LLM invoke failed: %s", exc)
        return None


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _serialize_company(company: Optional[Company]) -> Dict[str, Any]:
    if not company:
        return {}
    return {
        "company_id": str(company.id),
        "name": company.name,
        "sector": company.sector,
        "industry": company.industry,
        "ticker_nse": company.ticker_nse,
    }


# --------------------------------------------------------------------------- #
#  Candidate generation                                                       #
# --------------------------------------------------------------------------- #


def _commodity_candidates(
    db: Session, *, threshold: float = 4.0, lookback_days: int = 7
) -> List[Dict[str, Any]]:
    """Find commodity moves > threshold% over the lookback window."""
    codes = (
        db.query(CommoditySeries.code)
        .distinct()
        .all()
    )
    out: List[Dict[str, Any]] = []
    for (code,) in codes:
        delta = get_recent_series_change(table="commodity", code=code, lookback_days=lookback_days)
        pct = delta.get("pct_change")
        if pct is None or abs(pct) < threshold:
            continue
        links = (
            db.query(SectorCommodityLink)
            .filter(SectorCommodityLink.commodity_code == code)
            .all()
        )
        if not links:
            continue
        out.append(
            {
                "type": "causal_cross_industry",
                "trigger": {"commodity": code, "pct_change": pct, "delta": delta},
                "links": [
                    {
                        "scope_type": l.scope_type,
                        "scope_value": l.scope_value,
                        "role": l.role,
                        "weight": float(l.weight) if l.weight is not None else None,
                        "notes": l.notes,
                    }
                    for l in links
                ],
            }
        )
    return out


def _event_candidates(
    db: Session, *, since_days: int = 3, limit: int = 30
) -> List[Dict[str, Any]]:
    since = date.today() - timedelta(days=since_days)
    rows = (
        db.query(Event)
        .filter(Event.is_active.is_(True))
        .filter(Event.event_date >= since)
        .filter(Event.event_type.in_(["capex", "supply_disruption", "investor_meet", "regulation"]))
        .order_by(desc(Event.event_date))
        .limit(limit)
        .all()
    )
    return [
        {
            "type": "event_catalyst" if ev.event_type == "investor_meet" else "supply_chain_ripple",
            "event": {
                "id": str(ev.id),
                "company_id": str(ev.company_id) if ev.company_id else None,
                "event_type": ev.event_type,
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "headline": ev.headline,
                "structured": ev.structured_data or {},
                "evidence": ev.evidence_links or [],
            },
        }
        for ev in rows
    ]


def _sentiment_candidates(db: Session, *, since_days: int = 1, min_volume: int = 8) -> List[Dict[str, Any]]:
    since = datetime.utcnow() - timedelta(days=since_days)
    rows = (
        db.query(
            SocialPost.tickers,
            func.avg(SocialPost.sentiment_score).label("avg_score"),
            func.count(SocialPost.id).label("volume"),
        )
        .filter(SocialPost.posted_at >= since)
        .filter(SocialPost.tickers.isnot(None))
        .group_by(SocialPost.tickers)
        .all()
    )
    out: List[Dict[str, Any]] = []
    for tickers, avg_score, volume in rows:
        if volume < min_volume or avg_score is None:
            continue
        if abs(float(avg_score)) < 0.3:
            continue
        out.append(
            {
                "type": "sentiment_driven",
                "metrics": {
                    "tickers": tickers,
                    "avg_sentiment": float(avg_score),
                    "volume": int(volume),
                    "since": since.isoformat(),
                },
            }
        )
    return out[:10]


def _theme_breakouts(db: Session, *, since_days: int = 14, top: int = 10) -> List[Dict[str, Any]]:
    """Themes with rising company exposure - powers "what's trending" insights."""
    since = datetime.utcnow() - timedelta(days=since_days)
    rows = (
        db.query(
            CompanyTheme.theme_name,
            func.count(CompanyTheme.id).label("hits"),
            func.avg(CompanyTheme.impact_score).label("avg_impact"),
        )
        .filter(CompanyTheme.detected_at >= since)
        .filter(CompanyTheme.is_active.is_(True))
        .group_by(CompanyTheme.theme_name)
        .order_by(desc("hits"))
        .limit(top)
        .all()
    )
    out: List[Dict[str, Any]] = []
    for theme_name, hits, avg_impact in rows:
        if hits < 3:
            continue
        out.append(
            {
                "type": "causal_cross_industry",
                "trigger": {"theme": theme_name, "hits": int(hits), "avg_impact": float(avg_impact or 0.0)},
            }
        )
    return out


# --------------------------------------------------------------------------- #
#  InsightDiscoveryAgent                                                      #
# --------------------------------------------------------------------------- #


class InsightDiscoveryAgent:
    """Generate daily insight cards from the substrate."""

    def __init__(self, *, max_insights: int = 25):
        self.max_insights = max_insights

    def run(self, *, db: Optional[Session] = None) -> Dict[str, Any]:
        own = db is None
        db = db or SessionLocal()
        summary = {"created": 0, "skipped": 0, "templates_used": {}}
        try:
            candidates: List[Dict[str, Any]] = []
            candidates.extend(_commodity_candidates(db))
            candidates.extend(_event_candidates(db))
            candidates.extend(_sentiment_candidates(db))
            candidates.extend(_theme_breakouts(db))

            for cand in candidates[: self.max_insights]:
                template = cand["type"]
                summary["templates_used"].setdefault(template, 0)
                payload = self._build_card(db, cand)
                if not payload:
                    summary["skipped"] += 1
                    continue
                persisted = self._persist_insight(
                    db, template=template, payload=payload, candidate=cand
                )
                if persisted:
                    summary["templates_used"][template] += 1
                    summary["created"] += 1
                else:
                    summary["skipped"] += 1
            db.commit()
            return summary
        except Exception:
            db.rollback()
            raise
        finally:
            if own:
                db.close()

    # ------------------------------------------------------------------ #
    #  Per-candidate payload assembly                                    #
    # ------------------------------------------------------------------ #

    def _build_card(self, db: Session, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ctype = candidate.get("type")
        if ctype == "causal_cross_industry":
            return self._build_causal(db, candidate)
        if ctype == "supply_chain_ripple":
            return self._build_ripple(db, candidate)
        if ctype == "sentiment_driven":
            return self._build_sentiment(db, candidate)
        if ctype == "event_catalyst":
            return self._build_event(db, candidate)
        return None

    def _build_causal(self, db: Session, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        trigger = candidate.get("trigger") or {}
        links = candidate.get("links") or []
        themes = (
            db.query(CompanyTheme)
            .filter(CompanyTheme.is_active.is_(True))
            .order_by(desc(CompanyTheme.impact_score))
            .limit(20)
            .all()
        )
        events = (
            db.query(Event)
            .filter(Event.is_active.is_(True))
            .order_by(desc(Event.event_date))
            .limit(10)
            .all()
        )
        ctx = {
            "context": trigger,
            "links": links,
            "themes": [
                {
                    "company_id": str(t.company_id),
                    "theme": t.theme_name,
                    "impact": float(t.impact_score or 0),
                    "exposure": t.exposure_type,
                }
                for t in themes
            ],
            "events": [
                {
                    "id": str(e.id),
                    "type": e.event_type,
                    "date": e.event_date.isoformat() if e.event_date else None,
                    "headline": e.headline,
                }
                for e in events
            ],
        }
        messages = build_causal_cross_industry_messages(ctx)
        llm_text = _safe_llm_invoke(messages)
        parsed = _parse_json_block(llm_text or "") or self._fallback_causal(trigger, links)
        if not parsed or parsed.get("skip"):
            return None
        parsed.setdefault("predicted_direction", "up" if (trigger.get("pct_change") or 0) > 0 else "down")
        parsed.setdefault("horizon_days", 30)
        parsed.setdefault("evidence", self._evidence_from_trigger(trigger, links))
        return parsed

    def _build_ripple(self, db: Session, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event = candidate.get("event") or {}
        company_id = event.get("company_id")
        company = (
            db.query(Company).filter(Company.id == company_id).first() if company_id else None
        )
        snippets = []
        if company_id:
            news = (
                db.query(NewsArticle)
                .filter(NewsArticle.company_id == company_id)
                .order_by(desc(NewsArticle.published_at))
                .limit(5)
                .all()
            )
            snippets.extend({"source_type": "news", "source_id": str(n.id), "snippet": n.headline} for n in news)
        ctx = {
            "event": event,
            "edges": [],  # Lightweight Phase-1 - graph traversal is Phase-2
            "snippets": snippets,
            "primary": _serialize_company(company),
        }
        messages = build_supply_chain_ripple_messages(ctx)
        llm_text = _safe_llm_invoke(messages)
        parsed = _parse_json_block(llm_text or "") or self._fallback_ripple(event, company)
        if not parsed or parsed.get("skip"):
            return None
        parsed.setdefault("predicted_direction", "neutral")
        parsed.setdefault("horizon_days", 30)
        parsed.setdefault("evidence", event.get("evidence") or snippets[:1])
        return parsed

    def _build_sentiment(self, db: Session, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        metrics = candidate.get("metrics") or {}
        tickers = metrics.get("tickers") or []
        social = (
            db.query(SocialPost)
            .filter(SocialPost.tickers.overlap(tickers) if tickers else SocialPost.id.is_(None))
            .order_by(desc(SocialPost.posted_at))
            .limit(5)
            .all()
        )
        news = (
            db.query(NewsArticle)
            .filter(NewsArticle.tickers.overlap(tickers) if tickers else NewsArticle.id.is_(None))
            .order_by(desc(NewsArticle.published_at))
            .limit(3)
            .all()
        )
        ctx = {
            "metrics": metrics,
            "news": [{"source_type": "news", "source_id": str(n.id), "snippet": n.headline} for n in news],
            "social": [
                {
                    "source_type": "social",
                    "source_id": str(s.id),
                    "snippet": (s.body or "")[:160],
                    "stance": s.stance_label,
                    "sentiment": s.sentiment_label,
                }
                for s in social
            ],
        }
        messages = build_sentiment_driven_messages(ctx)
        llm_text = _safe_llm_invoke(messages)
        parsed = _parse_json_block(llm_text or "") or self._fallback_sentiment(metrics)
        if not parsed or parsed.get("skip"):
            return None
        parsed.setdefault("predicted_direction", "neutral")
        parsed.setdefault("horizon_days", 5)
        parsed.setdefault("evidence", ctx["social"][:1] + ctx["news"][:1])
        return parsed

    def _build_event(self, db: Session, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event = candidate.get("event") or {}
        ctx = {
            "event": event,
            "context": {},
            "positioning": [],
        }
        messages = build_event_catalyst_messages(ctx)
        llm_text = _safe_llm_invoke(messages)
        parsed = _parse_json_block(llm_text or "") or self._fallback_event(event)
        if not parsed or parsed.get("skip"):
            return None
        parsed.setdefault("predicted_direction", "neutral")
        parsed.setdefault("horizon_days", 14)
        parsed.setdefault("evidence", event.get("evidence") or [])
        return parsed

    # ------------------------------------------------------------------ #
    #  Heuristic fallbacks                                               #
    # ------------------------------------------------------------------ #

    def _fallback_causal(self, trigger: Dict[str, Any], links: List[Dict[str, Any]]) -> Dict[str, Any]:
        commodity = trigger.get("commodity") or trigger.get("theme")
        pct = trigger.get("pct_change")
        sectors = sorted({l.get("scope_value") for l in links if l.get("scope_value")})
        primary_sector = sectors[0] if sectors else None
        direction_phrase = (
            f"{abs(pct):.1f}% {'up' if pct and pct > 0 else 'down'}" if pct is not None else "shifting"
        )
        narrative = (
            f"{commodity} has moved {direction_phrase} over the last week. "
            f"Sector-commodity links flag {', '.join(sectors[:3]) or 'multiple sectors'} as exposed."
        )
        return {
            "headline": f"{commodity} move: watch {primary_sector or 'linked sectors'}",
            "narrative": narrative[:600],
            "predicted_direction": "up" if pct and pct > 0 else "down",
            "horizon_days": 30,
            "primary_companies": [],
            "related_themes": [],
            "related_sectors": sectors[:5],
            "evidence": self._evidence_from_trigger(trigger, links),
            "counter_evidence": [],
        }

    def _fallback_ripple(self, event: Dict[str, Any], company: Optional[Company]) -> Dict[str, Any]:
        name = company.name if company else event.get("headline") or "Source company"
        evidence = list(event.get("evidence") or [])
        if not evidence:
            evidence.append(
                {
                    "source_type": "event",
                    "source_id": str(event.get("id") or event.get("event_type") or "event"),
                    "snippet": (event.get("headline") or event.get("event_type") or "")[:160],
                }
            )
        return {
            "headline": f"Ripple watch: {name} {event.get('event_type','')}",
            "narrative": (
                f"{name} reported a {event.get('event_type')} event on "
                f"{event.get('event_date')}. Phase-1 lacks full supply-chain edges; "
                "review primary suppliers and customers manually."
            )[:600],
            "predicted_direction": "neutral",
            "horizon_days": 30,
            "primary_companies": [{"company_id": event.get("company_id"), "role": "source"}],
            "related_themes": [],
            "related_sectors": [company.sector] if company and company.sector else [],
            "evidence": evidence,
            "counter_evidence": [],
        }

    def _fallback_sentiment(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        tickers = metrics.get("tickers") or []
        evidence = [
            {
                "source_type": "social",
                "source_id": ",".join(tickers[:3]) or "social_aggregate",
                "snippet": (
                    f"avg_sentiment={metrics.get('avg_sentiment')} "
                    f"volume={metrics.get('volume')}"
                )[:160],
            }
        ]
        return {
            "headline": f"Social sentiment swing: {' '.join(tickers[:3])}",
            "narrative": (
                f"Average social sentiment for {', '.join(tickers[:3])} is "
                f"{metrics.get('avg_sentiment')} over {metrics.get('volume')} posts in the last 24h. "
                "Treat as speculative until corroborated by news/filings."
            )[:600],
            "predicted_direction": "neutral",
            "horizon_days": 5,
            "primary_companies": [],
            "related_themes": [],
            "related_sectors": [],
            "evidence": evidence,
            "counter_evidence": [],
        }

    def _fallback_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        evidence = list(event.get("evidence") or [])
        if not evidence:
            evidence.append(
                {
                    "source_type": "event",
                    "source_id": str(event.get("id") or event.get("event_type") or "event"),
                    "snippet": (event.get("headline") or event.get("event_type") or "")[:160],
                }
            )
        return {
            "headline": f"Catalyst: {event.get('headline','event')[:80]}",
            "narrative": (
                f"Scheduled {event.get('event_type')} on {event.get('event_date')} "
                f"for the linked company. Watch for guidance and structured commentary."
            )[:600],
            "predicted_direction": "neutral",
            "horizon_days": 14,
            "primary_companies": [{"company_id": event.get("company_id")}],
            "related_themes": [],
            "related_sectors": [],
            "evidence": evidence,
            "counter_evidence": [],
        }

    def _evidence_from_trigger(
        self, trigger: Dict[str, Any], links: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        ev: List[Dict[str, Any]] = []
        if trigger.get("commodity"):
            ev.append(
                {
                    "source_type": "commodity",
                    "source_id": trigger["commodity"],
                    "snippet": f"{trigger['commodity']} pct_change={trigger.get('pct_change')}",
                }
            )
        for link in links[:2]:
            ev.append(
                {
                    "source_type": "relation",
                    "source_id": f"{link.get('scope_type')}:{link.get('scope_value')}",
                    "snippet": f"role={link.get('role')} weight={link.get('weight')}",
                }
            )
        return ev or [{"source_type": "theme", "source_id": "trigger", "snippet": json.dumps(trigger)[:160]}]

    # ------------------------------------------------------------------ #
    #  Persistence                                                       #
    # ------------------------------------------------------------------ #

    def _persist_insight(
        self,
        db: Session,
        *,
        template: str,
        payload: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> bool:
        evidence = payload.get("evidence") or []
        if not evidence:
            logger.info("Skipping insight (template=%s) - no evidence", template)
            return False
        # Confidence scoring requires per-evidence observed_at; fall back to now.
        confidence_input = []
        for ev in evidence:
            confidence_input.append(
                {
                    "source_type": ev.get("source_type", "news"),
                    "source_name": ev.get("source_name"),
                    "observed_at": ev.get("observed_at") or datetime.utcnow(),
                }
            )
        conf = aggregate_confidence(confidence_input, db=db)

        insight = Insight(
            insight_type=template,
            headline=(payload.get("headline") or "Insight")[:500],
            narrative=(payload.get("narrative") or "")[:5000],
            primary_companies=payload.get("primary_companies") or [],
            related_themes=payload.get("related_themes") or [],
            related_sectors=payload.get("related_sectors") or [],
            related_policies=payload.get("related_policies") or [],
            predicted_direction=payload.get("predicted_direction"),
            horizon_days=int(payload.get("horizon_days", 30) or 30),
            score=to_decimal(conf["confidence"]),
            confidence=to_decimal(conf["confidence"]),
            confidence_components=conf["components"],
            evidence_links=evidence,
            counter_evidence=payload.get("counter_evidence") or [],
            status="active",
            generated_by=f"InsightDiscoveryAgent:{template}",
            generated_at=datetime.utcnow(),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=int(payload.get("horizon_days", 30) or 30)),
        )
        db.add(insight)
        db.flush()

        for ev in evidence:
            db.add(
                InsightEvidence(
                    insight_id=insight.id,
                    source_type=ev.get("source_type", "news"),
                    source_id=str(ev.get("source_id") or "")[:80],
                    snippet=(ev.get("snippet") or "")[:600],
                    weight=Decimal("0.7"),
                    metadata_={"candidate": candidate.get("type"), "raw": ev},
                )
            )
        return True
