"""Add mwrr_pct to performance_returns.

Revision ID: 0006_performance_mwrr
Revises: 0005_portfolio_extras
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_performance_mwrr"
down_revision = "0005_portfolio_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "performance_returns",
        sa.Column("mwrr_pct", sa.Numeric(9, 4), nullable=True),
        schema="performance",
    )


def downgrade() -> None:
    op.drop_column("performance_returns", "mwrr_pct", schema="performance")
