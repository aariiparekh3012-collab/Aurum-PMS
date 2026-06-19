"""Append-only audit logging helper (SEBI record retention).

Writes immutable audit rows. Never logs raw PII — only ids, actions and masked
references. Rows are write-once; updates/deletes are blocked at the DB grant level.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.infrastructure.db.models import AuditLogModel


class AuditLogger:
    def __init__(self, session: Session) -> None:
        self._s = session

    def record(
        self,
        *,
        aggregate_id: uuid.UUID,
        actor: str,
        action: str,
        payload: dict | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._s.add(
            AuditLogModel(
                aggregate_id=aggregate_id,
                actor=actor,
                action=action,
                payload=payload or {},
                correlation_id=correlation_id,
                created_at=dt.datetime.now(dt.timezone.utc),
            )
        )
        self._s.flush()
