"""Additive fixes needed to actually run the platform.

1. portfolio.portfolio_accounts.cash_balance_paise + portfolio.cash_ledger.description
2. Set DEFAULT now() on every NOT NULL timestamp column that lacks a default
   (the original migration declared created_at/updated_at/traded_at NOT NULL
   with no default, so inserts relying on ORM server_default failed).

Revision ID: 0005_portfolio_extras
Revises: 0004_auth
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_portfolio_extras"
down_revision = "0004_auth"
branch_labels = None
depends_on = None

_SCHEMAS = ("public", "client", "reference", "portfolio", "trading", "performance", "compliance", "notifications")


def upgrade() -> None:
    op.add_column(
        "portfolio_accounts",
        sa.Column("cash_balance_paise", sa.BigInteger(), nullable=False, server_default="0"),
        schema="portfolio",
    )
    op.add_column(
        "cash_ledger",
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        schema="portfolio",
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT table_schema, table_name, column_name FROM information_schema.columns "
            "WHERE data_type LIKE 'timestamp%' "
            "AND is_nullable = 'NO' AND column_default IS NULL "
            "AND table_schema = ANY(:schemas)"
        ),
        {"schemas": list(_SCHEMAS)},
    ).fetchall()
    for schema, table, column in rows:
        conn.execute(sa.text(f'ALTER TABLE "{schema}"."{table}" ALTER COLUMN "{column}" SET DEFAULT now()'))


def downgrade() -> None:
    op.drop_column("cash_ledger", "description", schema="portfolio")
    op.drop_column("portfolio_accounts", "cash_balance_paise", schema="portfolio")
