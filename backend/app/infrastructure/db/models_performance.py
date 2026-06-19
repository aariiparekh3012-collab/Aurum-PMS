"""SQLAlchemy ORM models for the `performance` schema."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ValuationSnapshotModel(Base):
    __tablename__ = "valuation_snapshots"
    __table_args__ = {"schema": "performance"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.portfolio_accounts.id", ondelete="CASCADE"), nullable=False
    )
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    market_value_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_value_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cash_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class PerformanceReturnModel(Base):
    __tablename__ = "performance_returns"
    __table_args__ = {"schema": "performance"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.portfolio_accounts.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(8), nullable=False)  # 1M, 3M, 6M, 1Y, 3Y, SI
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    twrr_pct: Mapped[float] = mapped_column(Numeric(9, 4), nullable=False)
    benchmark_pct: Mapped[float | None] = mapped_column(Numeric(9, 4))
