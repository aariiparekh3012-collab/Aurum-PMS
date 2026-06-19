"""SQLAlchemy ORM models for the `trading` schema."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Numeric, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.strategies.id"), nullable=False
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.securities_master.id"), nullable=False
    )
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    order_type: Mapped[str] = mapped_column(String(12), nullable=False, default="market")
    limit_price_paise: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_approval")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    allocations: Mapped[list["OrderAllocationModel"]] = relationship(back_populates="order")
    trades: Mapped[list["TradeModel"]] = relationship(back_populates="order")


class OrderAllocationModel(Base):
    __tablename__ = "order_allocations"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trading.orders.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.portfolio_accounts.id"), nullable=False
    )
    allocated_qty: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)

    order: Mapped[OrderModel] = relationship(back_populates="allocations")


class TradeModel(Base):
    __tablename__ = "trades"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trading.orders.id"), nullable=True
    )
    portfolio_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio.portfolio_accounts.id"), nullable=False
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.securities_master.id"), nullable=False
    )
    broker_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reference.brokers.id"), nullable=True
    )
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    traded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    contract_note: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped[OrderModel | None] = relationship(back_populates="trades")
