"""Add reference.security_prices table for daily close prices from NSE bhavcopy.

Revision ID: 0009_security_prices
Revises: 0008_messaging
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0009_security_prices"
down_revision = "0008_messaging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_prices",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "security_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("reference.securities_master.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("close_price_paise", sa.BigInteger(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False, server_default="0"),
        schema="reference",
    )
    op.create_index(
        "ix_security_prices_sec_date",
        "security_prices",
        ["security_id", "price_date"],
        unique=True,
        schema="reference",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_prices_sec_date",
        table_name="security_prices",
        schema="reference",
    )
    op.drop_table("security_prices", schema="reference")
