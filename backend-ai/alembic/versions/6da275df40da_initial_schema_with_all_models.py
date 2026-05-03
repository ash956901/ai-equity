"""initial schema baseline (existing tables)

Revision ID: 6da275df40da
Revises:
Create Date: 2026-03-22 21:33:59.158820

This baseline declares the schema as of the original implementation
(companies, securities, filings, news, portfolios, etc.). Production
environments that already used `init_db()` (Base.metadata.create_all)
should stamp this revision rather than running it. New environments can
run it to bootstrap.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from alembic import op


revision: str = "6da275df40da"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the baseline core tables, idempotently.

    We use ``create_table(..., if_not_exists=True)`` semantics by checking
    inspector first because Alembic's vanilla ``create_table`` errors if the
    table already exists. This keeps ``alembic upgrade head`` safe on
    existing databases that were bootstrapped via ``Base.metadata.create_all``.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    def _create(name: str, *args, **kwargs):
        if name not in existing:
            op.create_table(name, *args, **kwargs)

    _create(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(500)),
        sa.Column("ticker_nse", sa.String(20)),
        sa.Column("ticker_bse", sa.String(20)),
        sa.Column("isin", sa.String(12), unique=True),
        sa.Column("cin", sa.String(21)),
        sa.Column("sector", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("sub_industry", sa.String(100)),
        sa.Column("country", sa.String(3), server_default="IND"),
        sa.Column("website_domain", sa.String(255)),
        sa.Column("ir_page_url", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("market_cap_inr", sa.Integer),
        sa.Column("listing_status", sa.String(20), server_default="active"),
        sa.Column("listing_date", sa.Date),
        sa.Column("delisting_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "exchanges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("country", sa.String(3), server_default="IND"),
        sa.Column("timezone", sa.String(50), server_default="Asia/Kolkata"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "securities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exchange_id", UUID(as_uuid=True), sa.ForeignKey("exchanges.id"), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("isin", sa.String(12)),
        sa.Column("series", sa.String(10)),
        sa.Column("face_value", sa.Numeric(10, 2)),
        sa.Column("lot_size", sa.Integer),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "indices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("exchange_id", UUID(as_uuid=True), sa.ForeignKey("exchanges.id")),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "filings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exchange_id", UUID(as_uuid=True), sa.ForeignKey("exchanges.id")),
        sa.Column("filing_type", sa.String(100), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("filing_date", sa.Date, nullable=False),
        sa.Column("period_start", sa.Date),
        sa.Column("period_end", sa.Date),
        sa.Column("source_url", sa.Text),
        sa.Column("raw_uri", sa.Text),
        sa.Column("parsed_text_uri", sa.Text),
        sa.Column("document_hash", sa.String(64), unique=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("metadata", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "financial_statements_raw",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_filing_id", UUID(as_uuid=True), sa.ForeignKey("filings.id")),
        sa.Column("statement_type", sa.String(50), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("quarter", sa.Integer),
        sa.Column("is_audited", sa.Boolean, server_default=sa.false()),
        sa.Column("is_consolidated", sa.Boolean, server_default=sa.true()),
        sa.Column("line_item", sa.String(255), nullable=False),
        sa.Column("value", sa.Numeric(20, 2)),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("unit", sa.String(20), server_default="Cr"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "financial_ratios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("quarter", sa.Integer),
        sa.Column("roe", sa.Numeric(8, 4)),
        sa.Column("roce", sa.Numeric(8, 4)),
        sa.Column("roa", sa.Numeric(8, 4)),
        sa.Column("gross_margin", sa.Numeric(8, 4)),
        sa.Column("ebitda_margin", sa.Numeric(8, 4)),
        sa.Column("ebit_margin", sa.Numeric(8, 4)),
        sa.Column("net_margin", sa.Numeric(8, 4)),
        sa.Column("debt_to_equity", sa.Numeric(10, 4)),
        sa.Column("interest_coverage", sa.Numeric(10, 4)),
        sa.Column("current_ratio", sa.Numeric(8, 4)),
        sa.Column("pe_ratio", sa.Numeric(10, 4)),
        sa.Column("pb_ratio", sa.Numeric(10, 4)),
        sa.Column("ev_ebitda", sa.Numeric(10, 4)),
        sa.Column("price_to_sales", sa.Numeric(10, 4)),
        sa.Column("revenue_growth_yoy", sa.Numeric(8, 4)),
        sa.Column("pat_growth_yoy", sa.Numeric(8, 4)),
        sa.Column("eps_growth_yoy", sa.Numeric(8, 4)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "news_articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL")),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("body", sa.Text),
        sa.Column("source", sa.String(100)),
        sa.Column("source_url", sa.Text, unique=True),
        sa.Column("published_at", sa.DateTime, nullable=False),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("sentiment_score", sa.Numeric(5, 4)),
        sa.Column("sentiment_label", sa.String(20)),
        sa.Column("impact_level", sa.String(20)),
        sa.Column("relevance_confidence", sa.Numeric(4, 3)),
        sa.Column("affected_dimension", sa.String(50)),
        sa.Column("tickers", ARRAY(sa.String)),
        sa.Column("keywords", ARRAY(sa.String)),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "company_themes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("theme_name", sa.String(100), nullable=False),
        sa.Column("exposure_type", sa.String(50)),
        sa.Column("confidence_score", sa.Numeric(4, 3)),
        sa.Column("impact_score", sa.Numeric(4, 3)),
        sa.Column("reasoning", sa.Text),
        sa.Column("detected_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("validated_by", sa.String(50)),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("username", sa.String(100), unique=True),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("full_name", sa.String(255)),
        sa.Column("phone_number", sa.String(15)),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("address", sa.Text),
        sa.Column("pan_card_number", sa.String(10)),
        sa.Column("aadhaar_number", sa.String(12)),
        sa.Column("profile_pic_url", sa.Text),
        sa.Column("expertise_level", sa.String(20), server_default="beginner"),
        sa.Column("risk_tolerance", sa.String(20)),
        sa.Column("investment_horizon", sa.String(20)),
        sa.Column("kyc_status", sa.String(20), server_default="not_started"),
        sa.Column("kyc_submitted_at", sa.DateTime),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "portfolios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("broker", sa.String(50)),
        sa.Column("broker_account_id", sa.String(100)),
        sa.Column("is_primary", sa.Boolean, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "holdings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", UUID(as_uuid=True), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("average_price", sa.Numeric(15, 4)),
        sa.Column("current_price", sa.Numeric(15, 4)),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("last_updated", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("context_type", sa.String(50)),
        sa.Column("context_ids", JSON),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("last_message_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", JSON),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "user_uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL")),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50)),
        sa.Column("file_size_bytes", sa.Integer),
        sa.Column("raw_uri", sa.Text, nullable=False),
        sa.Column("parsed_text_uri", sa.Text),
        sa.Column("document_hash", sa.String(64)),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("vector_namespace", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "etl_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pipeline_name", sa.String(100), nullable=False),
        sa.Column("run_type", sa.String(20), server_default="scheduled"),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_processed", sa.Integer, server_default="0"),
        sa.Column("records_failed", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("metadata", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("condition_type", sa.String(50), nullable=False),
        sa.Column("condition_config", JSON),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("last_triggered_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "watchlists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "watchlist_companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("watchlist_id", UUID(as_uuid=True), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "saved_screens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filters", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "company_comparison_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payload", JSON, nullable=False),
        sa.Column("source", sa.String(50)),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create(
        "compare_flow_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), unique=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_a_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_b_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("flow_payload", JSON, nullable=False),
        sa.Column("result_payload", JSON, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop the baseline tables (best-effort - skips if absent)."""
    for table in [
        "compare_flow_logs",
        "company_comparison_snapshots",
        "saved_screens",
        "watchlist_companies",
        "watchlists",
        "alert_rules",
        "etl_runs",
        "user_uploads",
        "chat_messages",
        "chat_sessions",
        "holdings",
        "portfolios",
        "users",
        "company_themes",
        "news_articles",
        "financial_ratios",
        "financial_statements_raw",
        "filings",
        "indices",
        "securities",
        "exchanges",
        "companies",
    ]:
        try:
            op.drop_table(table)
        except Exception:
            pass
