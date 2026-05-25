"""add simulation_balance to users

Revision ID: a1b2c3d4e5f6
Revises: 6da275df40da
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "6da275df40da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("simulation_balance", sa.Float(), nullable=False, server_default="1000000"),
    )


def downgrade() -> None:
    op.drop_column("users", "simulation_balance")
