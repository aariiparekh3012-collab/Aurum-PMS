"""SQLAlchemy ORM models for the `notifications` schema."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActivityLogModel(Base):
    """Immutable activity stream — every significant action in the platform."""
    __tablename__ = "activity_log"
    __table_args__ = {"schema": "notifications"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_subject: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NotificationPreferenceModel(Base):
    """Per-user notification preferences (email, in-app toggles)."""
    __tablename__ = "preferences"
    __table_args__ = {"schema": "notifications"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_subject: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trade_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    application_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
