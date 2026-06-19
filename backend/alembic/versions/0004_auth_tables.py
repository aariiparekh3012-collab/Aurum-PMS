"""Auth tables — users, refresh tokens, password reset, email verification.

Revision ID: 0004_auth
Revises: 0003_notifications
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0004_auth"
down_revision = "0003_notifications"
branch_labels = None
depends_on = None


def _uuid_pk() -> sa.Column:
    return sa.Column("id", pg.UUID(as_uuid=True), primary_key=True)


def _ts(name: str, **kw) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), **kw)


def upgrade() -> None:
    # ── Users ─────────────────────────────────────────────────────────
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "client_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("client.clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _ts("created_at", nullable=False),
        _ts("updated_at", nullable=False),
        _ts("last_login_at", nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    # ── Refresh tokens ────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        _uuid_pk(),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("device_info", sa.String(256), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("expires_at", nullable=False),
        _ts("created_at", nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires", "refresh_tokens", ["expires_at"])

    # ── Password reset tokens ─────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        _uuid_pk(),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("expires_at", nullable=False),
        _ts("created_at", nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
    )

    # ── Email verification tokens ─────────────────────────────────────
    op.create_table(
        "email_verification_tokens",
        _uuid_pk(),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("expires_at", nullable=False),
        _ts("created_at", nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_email_verification_token_hash"),
    )


def downgrade() -> None:
    op.drop_table("email_verification_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
