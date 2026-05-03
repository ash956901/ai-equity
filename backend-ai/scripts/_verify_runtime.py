"""Runtime smoke-test for the Insight Engine implementation.

Boots an in-memory SQLite database with monkey-patched postgres-specific
types so we can exercise the actual SQLAlchemy models and ETL agents
without a real Postgres instance. Used by the verification step.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# ---- 1. Force SQLite + a temp DB file ---------------------------------------
DB_FILE = REPO_ROOT / ".verify.sqlite3"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

# ---- 2. Monkey-patch postgres types for SQLite ------------------------------
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.types import TypeDecorator, Text


class _JsonArray(TypeDecorator):
    """Store list[str] as JSON text on SQLite, list-comparable in Python."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return []


# pg.ARRAY(String) -> JSON text, pg.UUID -> CHAR(36), pg.JSON -> sa.JSON
class _Uuid(TypeDecorator):
    impl = sa.CHAR(36)
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__()

    def process_bind_param(self, value, dialect):
        return None if value is None else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            import uuid as _uuid

            return _uuid.UUID(value)
        except Exception:
            return value


pg.ARRAY = lambda *a, **kw: _JsonArray()  # noqa: E305
pg.UUID = _Uuid


# ---- 3. Now load the app modules --------------------------------------------
from src.db.database import Base, _get_engine  # noqa: E402
from src.db import models  # noqa: F401,E402

OK = "[ok]"
FAIL = "[fail]"


def step(name: str):
    print(f"\n=== {name} ===", flush=True)


def main() -> int:
    failures = 0

    step("create schema")
    try:
        engine = _get_engine()
        Base.metadata.create_all(engine)
        with engine.connect() as conn:
            from sqlalchemy import inspect

            insp = inspect(conn)
            tables = sorted(insp.get_table_names())
        new_tables = [
            "filing_pages",
            "theme_taxonomy",
            "policies",
            "events",
            "insights",
            "insight_evidence",
            "insight_outcomes",
            "transcripts",
            "transcript_segments",
            "social_posts",
            "social_topics",
            "macro_series",
            "commodity_series",
            "sector_commodity_links",
            "relation_edges",
            "source_quality",
        ]
        missing = [t for t in new_tables if t not in tables]
        print(f"  total tables: {len(tables)}")
        if missing:
            print(f"  {FAIL} missing: {missing}")
            failures += 1
        else:
            print(f"  {OK} all 16 new tables present")
    except Exception:
        traceback.print_exc()
        return 1

    step("seed source_quality + theme_taxonomy + sector_commodity_links")
    try:
        from src.etl.confidence import seed_source_quality
        from src.etl.theme_taxonomy_loader import seed_theme_taxonomy
        from src.etl.sector_commodity_loader import seed_sector_commodity_links

        sq = seed_source_quality()
        th = seed_theme_taxonomy()
        sc = seed_sector_commodity_links()
        print(f"  source_quality:  {sq}")
        print(f"  theme_taxonomy:  {th}")
        print(f"  sector_commodity:{sc}")
        if sq.get("created", 0) < 10 or th.get("created", 0) < 10 or sc.get("created", 0) < 5:
            print(f"  {FAIL} seed counts too low")
            failures += 1
        else:
            print(f"  {OK} seeders populated reference data")
    except Exception:
        traceback.print_exc()
        failures += 1

    step("synthesize a small dataset (companies, news, events, themes)")
    try:
        from src.db.database import SessionLocal
        from src.db.models import (
            Company,
            CompanyTheme,
            Event,
            NewsArticle,
            SectorCommodityLink,
        )

        db = SessionLocal()
        try:
            sugar = Company(
                name="Sample Sugar Mills",
                ticker_nse="SAMSUGAR",
                sector="Consumer",
                industry="Sugar",
                listing_status="active",
                country="IND",
            )
            lubri = Company(
                name="Sample Lubricants Ltd",
                ticker_nse="SAMLUB",
                sector="Industrials",
                industry="Lubricants",
                listing_status="active",
                country="IND",
            )
            db.add_all([sugar, lubri])
            db.commit()
            db.refresh(sugar)
            db.refresh(lubri)

            db.add_all(
                [
                    NewsArticle(
                        company_id=sugar.id,
                        headline="Government raises ethanol blending target to 20%",
                        body="The Cabinet approved an enhanced ethanol blending programme...",
                        source="Reuters",
                        source_url="https://example.com/eth-1",
                        published_at=datetime.utcnow(),
                        sentiment_score=Decimal("0.6"),
                        sentiment_label="positive",
                        impact_level="High",
                    ),
                    NewsArticle(
                        company_id=lubri.id,
                        headline="AI data centres demand specialty cooling fluids",
                        body="Hyperscale data centre buildouts are driving lubricants demand...",
                        source="Mint",
                        source_url="https://example.com/ai-lub-1",
                        published_at=datetime.utcnow(),
                        sentiment_score=Decimal("0.4"),
                        sentiment_label="positive",
                        impact_level="Medium",
                    ),
                ]
            )
            db.add_all(
                [
                    CompanyTheme(
                        company_id=sugar.id,
                        theme_name="ethanol_blending",
                        exposure_type="output",
                        confidence_score=Decimal("0.7"),
                        impact_score=Decimal("0.8"),
                        reasoning="Sugar mills produce ethanol",
                        validated_by="theme_tagging_agent",
                        is_active=True,
                    ),
                    CompanyTheme(
                        company_id=lubri.id,
                        theme_name="ai_data_centres",
                        exposure_type="customer",
                        confidence_score=Decimal("0.6"),
                        impact_score=Decimal("0.7"),
                        reasoning="Specialty lubricants for cooling",
                        validated_by="theme_tagging_agent",
                        is_active=True,
                    ),
                ]
            )
            db.add(
                Event(
                    company_id=sugar.id,
                    event_type="capex",
                    event_date=datetime.utcnow().date(),
                    headline="Sample Sugar to expand ethanol distillery capacity",
                    structured_data={"amount_cr": 250.0},
                    confidence=Decimal("0.6"),
                    is_active=True,
                )
            )
            db.commit()
            print(f"  {OK} dataset created: 2 companies, 2 news, 2 themes, 1 event")
        finally:
            db.close()
    except Exception:
        traceback.print_exc()
        failures += 1

    step("run InsightDiscoveryAgent (heuristic fallback - no LLM)")
    try:
        from src.agents.etl_agents import InsightDiscoveryAgent

        result = InsightDiscoveryAgent(max_insights=5).run()
        print(f"  result: {result}")
        if result.get("created", 0) == 0:
            print(f"  {FAIL} no insights produced")
            failures += 1
        else:
            print(f"  {OK} insights produced via heuristic fallback")
    except Exception:
        traceback.print_exc()
        failures += 1

    step("run EventExtractionAgent")
    try:
        from src.agents.etl_agents import EventExtractionAgent

        result = EventExtractionAgent().run()
        print(f"  result: {result}")
        print(f"  {OK} EventExtractionAgent completed without exception")
    except Exception:
        traceback.print_exc()
        failures += 1

    step("run InsightRevalidationAgent (no outcomes expected, agent must not crash)")
    try:
        from src.agents.etl_agents import InsightRevalidationAgent

        result = InsightRevalidationAgent().run()
        print(f"  result: {result}")
        print(f"  {OK} revalidation agent ran")
    except Exception:
        traceback.print_exc()
        failures += 1

    step("run graph_backfill + PatternMiningAgent")
    try:
        from src.agents.etl_agents import PatternMiningAgent, backfill_graph_edges

        bf = backfill_graph_edges()
        print(f"  backfill: {bf}")
        pm = PatternMiningAgent().run()
        print(f"  pattern mining: {pm}")
        print(f"  {OK} Phase-2 graph + pattern mining ran")
    except Exception:
        traceback.print_exc()
        failures += 1

    step("InsightsService.list_active_insights")
    try:
        from src.db.database import SessionLocal
        from src.domains.insights.service import InsightsService

        db = SessionLocal()
        try:
            feed = InsightsService(db).list_active_insights(limit=10)
            print(f"  total={feed['total']}, items={len(feed['items'])}")
            if feed["items"]:
                print(f"  first: {feed['items'][0]['headline'][:80]}")
            print(f"  {OK} feed served")
        finally:
            db.close()
    except Exception:
        traceback.print_exc()
        failures += 1

    print(f"\n=== summary: {failures} failure(s) ===")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
