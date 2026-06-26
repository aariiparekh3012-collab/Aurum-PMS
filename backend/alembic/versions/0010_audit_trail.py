"""Migrate audit_logs from public schema to audit schema with enhanced columns.

Revision ID: 0010_audit_trail
Revises: 0009_security_prices
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0010_audit_trail"
down_revision = "0009_security_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    # Drop the old basic audit_logs from the public schema (created in 0001)
    op.drop_index("ix_audit_aggregate", table_name="audit_logs")
    op.drop_table("audit_logs")

    # Create enhanced audit_logs in the audit schema
    op.create_table(
        "audit_logs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=True, index=True),
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("actor_email", sa.String(254), nullable=True),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("details", pg.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            index=True,
        ),
        schema="audit",
    )

    op.create_index(
        "ix_audit_logs_actor_time",
        "audit_logs",
        ["actor_id", "created_at"],
        schema="audit",
    )
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
        schema="audit",
    )


def downgrade() -> None:
    op.drop_table("audit_logs", schema="audit")
    op.execute("DROP SCHEMA IF EXISTS audit")

    # Restore the old public-schema audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("payload", pg.JSONB(), nullable=False),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_aggregate", "audit_logs", ["aggregate_id"])
