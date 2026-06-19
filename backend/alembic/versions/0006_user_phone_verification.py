"""Add phone + phone_verified to users and a phone_verification_codes table.

Supports phone (OTP) verification alongside the existing email verification flow.

Revision ID: 0006_user_phone
Revises: 0005_portfolio_extras
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0006_user_phone"
down_revision = "0005_portfolio_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.phone + users.phone_verified  (users live in the public schema)
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column(
        "users",
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # one-time phone OTP codes
    op.create_table(
        "phone_verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_phone_codes_user_id", "phone_verification_codes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_phone_codes_user_id", table_name="phone_verification_codes")
    op.drop_table("phone_verification_codes")
    op.drop_column("users", "phone_verified")
    op.drop_column("users", "phone")
