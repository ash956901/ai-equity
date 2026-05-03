"""insight engine tables (filing pages, events, policies, insights, transcripts, social, macro, relations, provenance)

Revision ID: a1b2c3d4e5f6
Revises: 6da275df40da
Create Date: 2026-05-03 03:40:00.000000

Adds the schema described in
/Users/shamanthh/.cursor/plans/equity_insight_engine_plan_82028662.plan.md
sections 3.4 and 3.7. All tables are guarded by inspector checks so the
migration is safe to re-run on databases that bootstrapped via
``Base.metadata.create_all``.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6da275df40da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    def _create(name: str, *args, **kwargs):
        if name not in existing:
            op.create_table(name, *args, **kwargs)

    def _index(name: str, table: str, columns):
        try:
            op.create_index(name, table, columns)
        except Exception:
            # Index may already exist (idempotent migration on legacy DBs)
            pass

    _create(
        "filing_pages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("filing_id", UUID(as_uuid=True), sa.ForeignKey("filings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("text", sa.Text),
        sa.Column("has_tables", sa.Boolean, server_default=sa.false()),
        sa.Column("has_charts", sa.Boolean, server_default=sa.false()),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("filing_id", "page_number", name="uq_filing_pages_filing_page"),
    )

    _create(
        "theme_taxonomy",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), unique=True, nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("category", sa.String(50)),
        sa.Column("description", sa.Text),
        sa.Column("keywords", ARRAY(sa.String)),
        sa.Column("parent_code", sa.String(64)),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(80), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("body", sa.Text),
        sa.Column("summary", sa.Text),
        sa.Column("issuer", sa.String(120)),
        sa.Column("effective_date", sa.Date),
        sa.Column("sectors_affected", ARRAY(sa.String)),
        sa.Column("themes", ARRAY(sa.String)),
        sa.Column("source_url", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL")),
        sa.Column("policy_id", UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_date", sa.Date),
        sa.Column("headline", sa.Text),
        sa.Column("structured_data", JSON),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("sentiment_label", sa.String(20)),
        sa.Column("source_filing_id", UUID(as_uuid=True), sa.ForeignKey("filings.id", ondelete="SET NULL")),
        sa.Column("source_news_id", UUID(as_uuid=True), sa.ForeignKey("news_articles.id", ondelete="SET NULL")),
        sa.Column("source_transcript_id", UUID(as_uuid=True)),
        sa.Column("evidence_links", JSON),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index("ix_events_company_date", "events", ["company_id", "event_date"])
    _index("ix_events_type_date", "events", ["event_type", "event_date"])

    _create(
        "insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("narrative", sa.Text),
        sa.Column("primary_companies", JSON),
        sa.Column("related_themes", ARRAY(sa.String)),
        sa.Column("related_sectors", ARRAY(sa.String)),
        sa.Column("related_policies", JSON),
        sa.Column("predicted_direction", sa.String(20)),
        sa.Column("horizon_days", sa.Integer),
        sa.Column("score", sa.Numeric(5, 4)),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("confidence_components", JSON),
        sa.Column("evidence_links", JSON),
        sa.Column("counter_evidence", JSON),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("generated_by", sa.String(80)),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("valid_from", sa.DateTime),
        sa.Column("valid_until", sa.DateTime),
        sa.Column("archived_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index("ix_insights_type_generated", "insights", ["insight_type", "generated_at"])
    _index("ix_insights_status_score", "insights", ["status", "score"])

    _create(
        "insight_evidence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("insight_id", UUID(as_uuid=True), sa.ForeignKey("insights.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", sa.String(80)),
        sa.Column("snippet", sa.Text),
        sa.Column("weight", sa.Numeric(4, 3)),
        sa.Column("metadata", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index("ix_insight_evidence_insight", "insight_evidence", ["insight_id"])
    _index("ix_insight_evidence_source", "insight_evidence", ["source_type", "source_id"])

    _create(
        "insight_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("insight_id", UUID(as_uuid=True), sa.ForeignKey("insights.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predicted_direction", sa.String(20)),
        sa.Column("horizon_days", sa.Integer),
        sa.Column("observed_return", sa.Numeric(10, 6)),
        sa.Column("observed_news_count", sa.Integer, server_default="0"),
        sa.Column("observed_signal", JSON),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("evaluated_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index("ix_insight_outcomes_status_eval", "insight_outcomes", ["status", "evaluated_at"])

    _create(
        "transcripts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fiscal_year", sa.Integer),
        sa.Column("fiscal_quarter", sa.Integer),
        sa.Column("period_end", sa.Date),
        sa.Column("title", sa.String(255)),
        sa.Column("source", sa.String(80)),
        sa.Column("source_url", sa.Text),
        sa.Column("raw_uri", sa.Text),
        sa.Column("parsed_text_uri", sa.Text),
        sa.Column("document_hash", sa.String(64), unique=True),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index("ix_transcripts_company_period", "transcripts", ["company_id", "fiscal_year", "fiscal_quarter"])

    _create(
        "transcript_segments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("transcript_id", UUID(as_uuid=True), sa.ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("speaker_name", sa.String(120)),
        sa.Column("speaker_role", sa.String(20)),
        sa.Column("speaker_org", sa.String(120)),
        sa.Column("turn_type", sa.String(20)),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("vector_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("transcript_id", "ordinal", name="uq_transcript_segments_transcript_ordinal"),
    )

    _create(
        "social_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("top_terms", ARRAY(sa.String)),
        sa.Column("centroid_vector_id", sa.String(64)),
        sa.Column("n_posts", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "social_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("source_post_id", sa.String(255), nullable=False),
        sa.Column("author_handle", sa.String(120)),
        sa.Column("author_followers", sa.Integer),
        sa.Column("posted_at", sa.DateTime, nullable=False),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("tickers", ARRAY(sa.String)),
        sa.Column("company_ids", JSON),
        sa.Column("sentiment_label", sa.String(20)),
        sa.Column("sentiment_score", sa.Numeric(5, 4)),
        sa.Column("stance_label", sa.String(20)),
        sa.Column("topic_id", UUID(as_uuid=True), sa.ForeignKey("social_topics.id", ondelete="SET NULL")),
        sa.Column("vector_id", sa.String(64)),
        sa.Column("raw", JSON),
        sa.Column("deleted_upstream_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_post_id", name="uq_social_posts_source_post"),
    )
    _index("ix_social_posts_posted_at", "social_posts", ["posted_at"])

    _create(
        "macro_series",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("series_label", sa.String(160)),
        sa.Column("observation_date", sa.Date, nullable=False),
        sa.Column("value", sa.Numeric(20, 6)),
        sa.Column("unit", sa.String(40)),
        sa.Column("source", sa.String(40), nullable=False, server_default="FRED"),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("code", "observation_date", name="uq_macro_series_code_date"),
    )

    _create(
        "commodity_series",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("series_label", sa.String(160)),
        sa.Column("observation_date", sa.Date, nullable=False),
        sa.Column("value", sa.Numeric(20, 6)),
        sa.Column("unit", sa.String(40)),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("code", "observation_date", name="uq_commodity_series_code_date"),
    )

    _create(
        "sector_commodity_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_value", sa.String(200), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE")),
        sa.Column("commodity_code", sa.String(50), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("weight", sa.Numeric(4, 3)),
        sa.Column("source", sa.String(80)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("scope_type", "scope_value", "commodity_code", "role", name="uq_sector_commodity_unique"),
    )

    _create(
        "relation_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_type", sa.String(30), nullable=False),
        sa.Column("subject_id", sa.String(120), nullable=False),
        sa.Column("predicate", sa.String(60), nullable=False),
        sa.Column("object_type", sa.String(30), nullable=False),
        sa.Column("object_id", sa.String(120), nullable=False),
        sa.Column("weight", sa.Numeric(5, 4)),
        sa.Column("evidence_id", sa.String(80)),
        sa.Column("source", sa.String(80)),
        sa.Column("valid_from", sa.DateTime),
        sa.Column("valid_to", sa.DateTime),
        sa.Column("metadata", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "subject_type", "subject_id", "predicate", "object_type", "object_id",
            name="uq_relation_edges_triple",
        ),
    )
    _index("ix_relation_edges_subject", "relation_edges", ["subject_type", "subject_id"])
    _index("ix_relation_edges_object", "relation_edges", ["object_type", "object_id"])

    _create(
        "source_quality",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("quality_score", sa.Numeric(4, 3), server_default="0.5"),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("source_type", "source_name", name="uq_source_quality_type_name"),
    )


def downgrade() -> None:
    for table in [
        "source_quality",
        "relation_edges",
        "sector_commodity_links",
        "commodity_series",
        "macro_series",
        "social_posts",
        "social_topics",
        "transcript_segments",
        "transcripts",
        "insight_outcomes",
        "insight_evidence",
        "insights",
        "events",
        "policies",
        "theme_taxonomy",
        "filing_pages",
    ]:
        try:
            op.drop_table(table)
        except Exception:
            pass
