"""add simulated_trades and simulator_stats tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-26 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulated_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("ticker", sa.String(30), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("trade_type", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_at_trade", sa.Float(), nullable=False),
        sa.Column("total_value", sa.Float(), nullable=False),
        sa.Column("pnl_at_close", sa.Float(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("opened_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_simulated_trades_user_status", "simulated_trades", ["user_id", "status"])

    op.create_table(
        "simulator_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("badges", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winning_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_challenge_last", sa.String(50), nullable=True),
        sa.Column("daily_challenge_done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_simulator_stats_user_id", "simulator_stats", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_simulator_stats_user_id", "simulator_stats")
    op.drop_table("simulator_stats")
    op.drop_index("ix_simulated_trades_user_status", "simulated_trades")
    op.drop_table("simulated_trades")
