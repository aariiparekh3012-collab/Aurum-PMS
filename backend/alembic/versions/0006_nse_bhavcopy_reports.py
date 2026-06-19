"""Add nse_bhavcopy_reports table for daily NSE CM-UDiFF Bhavcopy downloads.

TARGET DATABASE: downloaddailyreport (NOT the main pms database).
Run with:
    alembic -x db=nse upgrade head
or connect alembic directly to downloaddailyreport via NSE_DATABASE_URL.

Revision ID: 0006_nse_bhavcopy_reports
Revises: 0005_portfolio_extras
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0006_nse_bhavcopy_reports"
down_revision = "0005_portfolio_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nse_bhavcopy_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("file_date", sa.Date(), nullable=False),
        sa.Column("file_name", sa.String(200), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_nse_bhavcopy_file_date",
        "nse_bhavcopy_reports",
        ["file_date"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_nse_bhavcopy_file_date", table_name="nse_bhavcopy_reports", schema="public")
    op.drop_table("nse_bhavcopy_reports", schema="public")
