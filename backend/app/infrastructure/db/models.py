"""SQLAlchemy ORM models — the persistence representation of the aggregate.

Deliberately separate from domain entities (Data Mapper, not Active Record).
PII columns store encrypted ciphertext; only masked/derived values are queryable.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OnboardingApplicationModel(Base):
    __tablename__ = "onboarding_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    investor_type: Mapped[str] = mapped_column(String(20), nullable=False)

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)

    # PAN is hashed (for uniqueness lookups) AND stored encrypted.
    pan_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    pan_enc: Mapped[str] = mapped_column(Text, nullable=False)

    aadhaar_last4: Mapped[str | None] = mapped_column(String(4))
    aadhaar_enc: Mapped[str | None] = mapped_column(Text)

    bank_account_enc: Mapped[str | None] = mapped_column(Text)
    bank_ifsc: Mapped[str | None] = mapped_column(String(11))
    bank_holder_name: Mapped[str | None] = mapped_column(String(200))

    demat_bo_id: Mapped[str | None] = mapped_column(String(16))
    demat_depository: Mapped[str | None] = mapped_column(String(4))

    proposed_investment_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    kyc_source: Mapped[str | None] = mapped_column(String(10))
    kyc_reference: Mapped[str | None] = mapped_column(String(64))
    risk_category: Mapped[str | None] = mapped_column(String(20))
    risk_score: Mapped[int | None] = mapped_column(Integer)
    agreement_esign_ref: Mapped[str | None] = mapped_column(String(64))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    documents: Mapped[list["OnboardingDocumentModel"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_onboarding_status_created", "status", "created_at"),)


class OnboardingDocumentModel(Base):
    __tablename__ = "onboarding_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("onboarding_applications.id", ondelete="CASCADE"), index=True
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Documents live in object storage (S3); DB keeps the key + integrity hash only.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    application: Mapped[OnboardingApplicationModel] = relationship(back_populates="documents")


class AuditLogModel(Base):
    """Append-only audit trail (SEBI record-keeping). No updates/deletes allowed."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxModel(Base):
    """Transactional outbox — domain events persisted with the same DB transaction."""

    __tablename__ = "event_outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    published: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
