"""auth user extensions: email_verified_at, last_login_at, avatar_url,
theme_preference, default_chart_range, sectors_of_interest.

Revision ID: c1d2e3f4a501
Revises: b7c2e1d34a01
Create Date: 2026-05-03 06:00:00.000000

Idempotent: every column add is gated by an inspector check.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op


revision: str = "c1d2e3f4a501"
down_revision: Union[str, Sequence[str], None] = "b7c2e1d34a01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _add_column(bind, table: str, column: sa.Column) -> None:
    if column.name in _columns(bind, table):
        return
    op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    _add_column(bind, "users", sa.Column("email_verified_at", sa.DateTime, nullable=True))
    _add_column(bind, "users", sa.Column("last_login_at", sa.DateTime, nullable=True))
    _add_column(bind, "users", sa.Column("avatar_url", sa.Text, nullable=True))
    _add_column(bind, "users", sa.Column("theme_preference", sa.String(20), nullable=True))
    _add_column(bind, "users", sa.Column("default_chart_range", sa.String(10), nullable=True))
    _add_column(bind, "users", sa.Column("sectors_of_interest", ARRAY(sa.String), nullable=True))


def downgrade() -> None:
    for col in (
        "sectors_of_interest",
        "default_chart_range",
        "theme_preference",
        "avatar_url",
        "last_login_at",
        "email_verified_at",
    ):
        try:
            op.drop_column("users", col)
        except Exception:
            pass
