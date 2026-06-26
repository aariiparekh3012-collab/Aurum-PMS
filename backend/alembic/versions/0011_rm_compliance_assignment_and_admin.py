"""Add RM/Compliance assignment columns and admin role support.

Revision ID: 0011_assignments
Revises: 0010_audit_trail
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0011_assignments"
down_revision = "0010_audit_trail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add assigned_rm_id and assigned_compliance_id to onboarding_applications
    op.add_column(
        "onboarding_applications",
        sa.Column("assigned_rm_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "onboarding_applications",
        sa.Column("assigned_compliance_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    # Add assigned_rm_id and assigned_compliance_id to client.clients
    op.add_column(
        "clients",
        sa.Column("assigned_rm_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        schema="client",
    )
    op.add_column(
        "clients",
        sa.Column("assigned_compliance_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        schema="client",
    )


def downgrade() -> None:
    op.drop_column("clients", "assigned_compliance_id", schema="client")
    op.drop_column("clients", "assigned_rm_id", schema="client")
    op.drop_column("onboarding_applications", "assigned_compliance_id")
    op.drop_column("onboarding_applications", "assigned_rm_id")
