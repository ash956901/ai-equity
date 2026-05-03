"""discovery extensions: chart_series, statement_items, company_web_endpoints,
system_config, filing_summaries, transactions, alert_events; companies and
company_themes column extensions.

Revision ID: b7c2e1d34a01
Revises: a1b2c3d4e5f6
Create Date: 2026-05-03 04:00:00.000000

Adds the schema described in the "Hidden Insights & Industries" plan
(Phase A2). All operations are guarded so the migration is safe to re-run
on databases that bootstrapped via ``Base.metadata.create_all``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op


revision: str = "b7c2e1d34a01"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table: str) -> set[str]:
    inspector = sa.inspect(bind)
    if table not in set(inspector.get_table_names()):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def _create(name: str, existing: set[str], *args, **kwargs) -> None:
    if name not in existing:
        op.create_table(name, *args, **kwargs)


def _add_column(bind, table: str, column: sa.Column) -> None:
    if table in _existing_tables(bind) and column.name not in _columns(bind, table):
        op.add_column(table, column)


def _index(name: str, table: str, columns, **kwargs) -> None:
    try:
        op.create_index(name, table, columns, **kwargs)
    except Exception:
        # Index may already exist (idempotent on legacy DBs).
        pass


def upgrade() -> None:
    bind = op.get_bind()
    existing = _existing_tables(bind)

    # ------------------------------------------------------------------
    # companies extensions
    # ------------------------------------------------------------------
    _add_column(
        bind,
        "companies",
        sa.Column("thematic_exposure_summary", JSON, nullable=True),
    )
    _add_column(
        bind,
        "companies",
        sa.Column("macro_sensitivity", JSON, nullable=True),
    )
    _add_column(
        bind,
        "companies",
        sa.Column("supply_chain_summary", JSON, nullable=True),
    )

    # ------------------------------------------------------------------
    # company_themes extensions
    # ------------------------------------------------------------------
    _add_column(
        bind,
        "company_themes",
        sa.Column("impact_direction", sa.String(10), nullable=True),
    )
    _add_column(
        bind,
        "company_themes",
        sa.Column("impact_horizon", sa.String(20), nullable=True),
    )
    _add_column(
        bind,
        "company_themes",
        sa.Column(
            "is_asymmetric",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    _add_column(
        bind,
        "company_themes",
        sa.Column("evidence_quotes", JSON, nullable=True),
    )
    _index(
        "ix_company_themes_company_theme",
        "company_themes",
        ["company_id", "theme_name"],
        unique=True,
    )
    _index(
        "ix_company_themes_asymmetric",
        "company_themes",
        ["is_asymmetric", "confidence_score"],
    )

    # ------------------------------------------------------------------
    # chart_series
    # ------------------------------------------------------------------
    _create(
        "chart_series",
        existing,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "filing_id",
            UUID(as_uuid=True),
            sa.ForeignKey("filings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer),
        sa.Column("chart_type", sa.String(40)),
        sa.Column("title", sa.String(255)),
        sa.Column("series_name", sa.String(120)),
        sa.Column("units", sa.String(40)),
        sa.Column("data_points", JSON),
        sa.Column("extraction_model", sa.String(80)),
        sa.Column("extraction_confidence", sa.Numeric(4, 3)),
        sa.Column("extracted_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index("ix_chart_series_filing", "chart_series", ["filing_id", "page_number"])

    # ------------------------------------------------------------------
    # statement_items
    # ------------------------------------------------------------------
    _create(
        "statement_items",
        existing,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "filing_id",
            UUID(as_uuid=True),
            sa.ForeignKey("filings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("statement_type", sa.String(20), nullable=False),
        sa.Column("line_item", sa.String(255), nullable=False),
        sa.Column("value", sa.Numeric(20, 4)),
        sa.Column("currency", sa.String(3), server_default="INR"),
        sa.Column("units", sa.String(20)),
        sa.Column("segment", sa.String(120)),
        sa.Column("geography", sa.String(80)),
        sa.Column("is_consolidated", sa.Boolean, server_default=sa.true()),
        sa.Column("extracted_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index(
        "ix_statement_items_lookup",
        "statement_items",
        [
            "company_id",
            "period_end",
            "statement_type",
            "line_item",
            "segment",
            "geography",
        ],
    )

    # ------------------------------------------------------------------
    # company_web_endpoints
    # ------------------------------------------------------------------
    _create(
        "company_web_endpoints",
        existing,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("endpoint_type", sa.String(40), nullable=False),
        sa.Column("discovered_via", sa.String(40)),
        sa.Column("last_crawled_at", sa.DateTime),
        sa.Column("last_status", sa.String(20)),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index(
        "ix_company_web_endpoints_unique",
        "company_web_endpoints",
        ["company_id", "url"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # system_config
    # ------------------------------------------------------------------
    _create(
        "system_config",
        existing,
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("value", JSON),
        sa.Column("description", sa.Text),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ------------------------------------------------------------------
    # filing_summaries (AI one-liners feeding the Timeline)
    # ------------------------------------------------------------------
    _create(
        "filing_summaries",
        existing,
        sa.Column(
            "filing_id",
            UUID(as_uuid=True),
            sa.ForeignKey("filings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("summary_one_liner", sa.Text, nullable=False),
        sa.Column("event_type", sa.String(40)),
        sa.Column("materiality_score", sa.Numeric(4, 3)),
        sa.Column("sentiment", sa.String(20)),
        sa.Column("affected_dimension", sa.String(50)),
        sa.Column("model_used", sa.String(80)),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ------------------------------------------------------------------
    # transactions
    # ------------------------------------------------------------------
    _create(
        "transactions",
        existing,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id"),
            nullable=False,
        ),
        sa.Column("txn_type", sa.String(20), nullable=False),
        sa.Column("txn_date", sa.Date, nullable=False),
        sa.Column("quantity", sa.Numeric(15, 4), nullable=False),
        sa.Column("price_inr", sa.Numeric(15, 4)),
        sa.Column("fees_inr", sa.Numeric(15, 4)),
        sa.Column("broker_txn_id", sa.String(100)),
        sa.Column("source", sa.String(40)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    _index(
        "ix_transactions_portfolio_date",
        "transactions",
        ["portfolio_id", "txn_date"],
    )
    _index(
        "ix_transactions_broker_unique",
        "transactions",
        ["portfolio_id", "broker_txn_id"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # alert_events
    # ------------------------------------------------------------------
    _create(
        "alert_events",
        existing,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rule_id",
            UUID(as_uuid=True),
            sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id"),
            nullable=True,
        ),
        sa.Column("triggered_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("payload", JSON),
        sa.Column("delivery_status", sa.String(20), server_default="pending"),
        sa.Column("delivered_at", sa.DateTime),
    )
    _index("ix_alert_events_user_time", "alert_events", ["user_id", "triggered_at"])
    _index("ix_alert_events_rule_time", "alert_events", ["rule_id", "triggered_at"])


def downgrade() -> None:
    for table in [
        "alert_events",
        "transactions",
        "filing_summaries",
        "system_config",
        "company_web_endpoints",
        "statement_items",
        "chart_series",
    ]:
        try:
            op.drop_table(table)
        except Exception:
            pass

    for col in (
        "evidence_quotes",
        "is_asymmetric",
        "impact_horizon",
        "impact_direction",
    ):
        try:
            op.drop_column("company_themes", col)
        except Exception:
            pass

    for col in (
        "supply_chain_summary",
        "macro_sensitivity",
        "thematic_exposure_summary",
    ):
        try:
            op.drop_column("companies", col)
        except Exception:
            pass
