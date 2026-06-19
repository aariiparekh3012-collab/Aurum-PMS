"""SQLAlchemy ORM models for the `portfolio` schema."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Numeric, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FeeScheduleModel(Base):
    __tablename__ = "fee_schedules"
    __table_args__ = {"schema": "portfolio"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    mgmt_fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    perf_fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    high_water_mark: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hurdle_rate_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))


class PortfolioAccountModel(Base):
    __tablename__ = "portfolio_accounts"
    __table_args__ = {"schema": "portfolio"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.clients.id"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.strategies.id"), nullable=False
    )
    demat_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("client.client_demat_accounts.id"), nullable=True
    )
    fee_schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portfolio.fee_schedules.id"), nullable=True
    )
    account_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    inception_date: Mapped[date] = mapped_column(Date, nullable=False)
    cash_balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    holdings: Mapped[list["HoldingModel"]] = relationship(back_populates="portfolio_account")


class HoldingModel(Base):
    __tablename__ = "holdings"
    __table_args__ = {"schema": "portfolio"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.portfolio_accounts.id", ondelete="CASCADE"), nullable=False
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.securities_master.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    avg_cost_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    portfolio_account: Mapped[PortfolioAccountModel] = relationship(back_populates="holdings")
    lots: Mapped[list["HoldingLotModel"]] = relationship(
        back_populates="holding", cascade="all, delete-orphan"
    )


class HoldingLotModel(Base):
    __tablename__ = "holding_lots"
    __table_args__ = {"schema": "portfolio"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    holding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.holdings.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    cost_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    acquired_on: Mapped[date] = mapped_column(Date, nullable=False)

    holding: Mapped[HoldingModel] = relationship(back_populates="lots")


class CashLedgerModel(Base):
    __tablename__ = "cash_ledger"
    __table_args__ = {"schema": "portfolio"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.portfolio_accounts.id", ondelete="CASCADE"), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(String(24), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    posted_on: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CapitalFlowModel(Base):
    __tablename__ = "capital_flows"
    __table_args__ = {"schema": "portfolio"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.portfolio_accounts.id", ondelete="CASCADE"), nullable=False
    )
    flow_type: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="cash")
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    value_date: Mapped[date] = mapped_column(Date, nullable=False)
