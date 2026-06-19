"""SQLAlchemy ORM models for the `client` schema (Client Master module).

Kept in a separate file so the onboarding models remain untouched. All tables live
in the PostgreSQL `client` schema. PII columns store encrypted ciphertext.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClientModel(Base):
    __tablename__ = "clients"
    __table_args__ = {"schema": "client"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    onboarding_application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("onboarding_applications.id"),
        unique=True,
        nullable=False,
    )
    client_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    pan_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    pan_enc: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    investor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    bank_accounts: Mapped[list["ClientBankAccountModel"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    demat_accounts: Mapped[list["ClientDematAccountModel"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    nominees: Mapped[list["NomineeModel"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    risk_profiles: Mapped[list["ClientRiskProfileModel"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class ClientBankAccountModel(Base):
    __tablename__ = "client_bank_accounts"
    __table_args__ = {"schema": "client"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.clients.id", ondelete="CASCADE"), nullable=False
    )
    account_enc: Mapped[str] = mapped_column(Text, nullable=False)
    ifsc: Mapped[str] = mapped_column(String(11), nullable=False)
    holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    client: Mapped[ClientModel] = relationship(back_populates="bank_accounts")


class ClientDematAccountModel(Base):
    __tablename__ = "client_demat_accounts"
    __table_args__ = {"schema": "client"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.clients.id", ondelete="CASCADE"), nullable=False
    )
    bo_id: Mapped[str] = mapped_column(String(16), nullable=False)
    depository: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    client: Mapped[ClientModel] = relationship(back_populates="demat_accounts")


class NomineeModel(Base):
    __tablename__ = "nominees"
    __table_args__ = {"schema": "client"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.clients.id", ondelete="CASCADE"), nullable=False
    )
    name_enc: Mapped[str] = mapped_column(Text, nullable=False)
    relationship_: Mapped[str | None] = mapped_column("relationship", String(40))
    share_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    client: Mapped[ClientModel] = relationship(back_populates="nominees")


class ClientRiskProfileModel(Base):
    __tablename__ = "client_risk_profiles"
    __table_args__ = {"schema": "client"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.clients.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    ruleset_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    effective_from: Mapped[dt.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    client: Mapped[ClientModel] = relationship(back_populates="risk_profiles")
