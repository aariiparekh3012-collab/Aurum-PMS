"""SQLAlchemy ORM model for the append-only audit log (SEBI record-keeping).

Enhanced schema: tracks actor identity, role, event classification,
resource references, IP address, and user agent for full compliance trail.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLogModel(Base):
    """Append-only audit trail (SEBI record-keeping). No updates/deletes allowed."""

    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "audit"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # What happened
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Who did it
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(254), nullable=True)

    # What was affected
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Context
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
