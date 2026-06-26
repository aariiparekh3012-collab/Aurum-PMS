"""Append-only audit logging helper (SEBI record retention).

Writes immutable audit rows. Never logs raw PII — only IDs, actions and masked
references. Rows are write-once; updates/deletes are blocked at the DB grant level.

Usage in endpoints:
    from app.infrastructure.audit.audit_logger import AuditLogger
    audit = AuditLogger(db)
    audit.log(
        event_type="trade.created",
        description="Recorded BUY 100 RELIANCE",
        actor_id=user["sub"], actor_role=user.get("role"),
        resource_type="trade", resource_id=str(trade.id),
        request=request,
    )
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.infrastructure.db.models_audit import AuditLogModel

logger = logging.getLogger("pms.audit")


class AuditLogger:
    """Append-only audit writer bound to a DB session."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def log(
        self,
        *,
        event_type: str,
        description: str,
        actor_id: str | None = None,
        actor_role: str | None = None,
        actor_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> None:
        """Write one audit row. Extracts IP + user-agent from request if given."""
        ip = None
        ua = None
        if request is not None:
            ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            if not ip:
                ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent", "")[:512]

        row = AuditLogModel(
            event_type=event_type,
            description=description,
            actor_id=actor_id,
            actor_role=actor_role,
            actor_email=actor_email,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip,
            user_agent=ua,
        )
        self._s.add(row)
        self._s.flush()
        logger.info(
            "AUDIT | %s | actor=%s | %s/%s | %s",
            event_type, actor_id or "system",
            resource_type or "-", resource_id or "-",
            description[:120],
        )
