"""SQLAlchemy ORM models for the `reference` schema."""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Boolean, Date, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SecurityModel(Base):
    __tablename__ = "securities_master"
    __table_args__ = {"schema": "reference"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isin: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class BenchmarkModel(Base):
    __tablename__ = "benchmarks"
    __table_args__ = {"schema": "reference"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    values: Mapped[list["BenchmarkValueModel"]] = relationship(back_populates="benchmark")


class BenchmarkValueModel(Base):
    __tablename__ = "benchmark_values"
    __table_args__ = {"schema": "reference"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.benchmarks.id", ondelete="CASCADE"), nullable=False
    )
    as_of: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    index_level: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    benchmark: Mapped[BenchmarkModel] = relationship(back_populates="values")


class StrategyModel(Base):
    __tablename__ = "strategies"
    __table_args__ = {"schema": "reference"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    approach: Mapped[str] = mapped_column(String(40), nullable=False)
    benchmark_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reference.benchmarks.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    constituents: Mapped[list["StrategyConstituentModel"]] = relationship(back_populates="strategy")


class StrategyConstituentModel(Base):
    __tablename__ = "strategy_constituents"
    __table_args__ = {"schema": "reference"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.strategies.id", ondelete="CASCADE"), nullable=False
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.securities_master.id"), nullable=False
    )
    target_weight: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)

    strategy: Mapped[StrategyModel] = relationship(back_populates="constituents")


class BrokerModel(Base):
    __tablename__ = "brokers"
    __table_args__ = {"schema": "reference"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sebi_reg_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
