"""Add sales.cancelled_at for cancel/refund

Revision ID: 004
Revises: 003
Create Date: 2026-11-07 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sales_cancelled_at", "sales", ["cancelled_at"])


def downgrade() -> None:
    op.drop_index("ix_sales_cancelled_at", table_name="sales")
    op.drop_column("sales", "cancelled_at")
