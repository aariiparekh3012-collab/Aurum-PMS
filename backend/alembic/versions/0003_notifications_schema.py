"""notifications schema — activity log + user preferences

Revision ID: 0003_notifications
Revises: 0002_platform
Create Date: 2026-06-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0003_notifications"
down_revision = "0002_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "notifications"')

    op.create_table(
        "activity_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("actor_subject", sa.String(120), nullable=False),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("detail", sa.Text()),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="notifications",
    )
    op.create_index(
        "ix_activity_log_entity_type",
        "activity_log",
        ["entity_type"],
        schema="notifications",
    )
    op.create_index(
        "ix_activity_log_is_read",
        "activity_log",
        ["is_read"],
        schema="notifications",
    )
    op.create_index(
        "ix_activity_log_created_at",
        "activity_log",
        ["created_at"],
        schema="notifications",
    )

    op.create_table(
        "preferences",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_subject", sa.String(120), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("trade_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "application_alerts", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.UniqueConstraint("user_subject", name="uq_preferences_user_subject"),
        schema="notifications",
    )


def downgrade() -> None:
    op.execute('DROP SCHEMA IF EXISTS "notifications" CASCADE')
