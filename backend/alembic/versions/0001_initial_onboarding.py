"""initial onboarding schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("investor_type", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=False),
        sa.Column("pan_hash", sa.String(64), nullable=False),
        sa.Column("pan_enc", sa.Text(), nullable=False),
        sa.Column("aadhaar_last4", sa.String(4)),
        sa.Column("aadhaar_enc", sa.Text()),
        sa.Column("bank_account_enc", sa.Text()),
        sa.Column("bank_ifsc", sa.String(11)),
        sa.Column("bank_holder_name", sa.String(200)),
        sa.Column("demat_bo_id", sa.String(16)),
        sa.Column("demat_depository", sa.String(4)),
        sa.Column("proposed_investment_paise", sa.BigInteger(), nullable=False),
        sa.Column("kyc_source", sa.String(10)),
        sa.Column("kyc_reference", sa.String(64)),
        sa.Column("risk_category", sa.String(20)),
        sa.Column("risk_score", sa.Integer()),
        sa.Column("agreement_esign_ref", sa.String(64)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("pan_hash", name="uq_onboarding_pan_hash"),
    )
    op.create_index("ix_onboarding_status", "onboarding_applications", ["status"])
    op.create_index("ix_onboarding_email", "onboarding_applications", ["email"])
    op.create_index(
        "ix_onboarding_status_created", "onboarding_applications", ["status", "created_at"]
    )

    op.create_table(
        "onboarding_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("onboarding_applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_application", "onboarding_documents", ["application_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_aggregate", "audit_logs", ["aggregate_id"])

    op.create_table(
        "event_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outbox_aggregate", "event_outbox", ["aggregate_id"])
    op.create_index("ix_outbox_published", "event_outbox", ["published"])


def downgrade() -> None:
    op.drop_table("event_outbox")
    op.drop_table("audit_logs")
    op.drop_table("onboarding_documents")
    op.drop_table("onboarding_applications")
