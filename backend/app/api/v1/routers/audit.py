"""Audit trail API — read-only access for compliance officers."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func as sa_func, select, desc, and_
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models_audit import AuditLogModel

router = APIRouter(prefix="/audit", tags=["audit"])


# ── Schemas ────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: uuid.UUID
    event_type: str
    description: str
    actor_id: str | None = None
    actor_role: str | None = None
    actor_email: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogPage(BaseModel):
    logs: list[AuditLogOut]
    total: int
    limit: int
    offset: int


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/logs", response_model=AuditLogPage)
def list_audit_logs(
    event_type: str | None = Query(None, description="Filter by event type prefix, e.g. 'auth' or 'trade.recorded'"),
    actor_id: str | None = Query(None, description="Filter by actor (user sub)"),
    resource_type: str | None = Query(None, description="Filter by resource type, e.g. 'order', 'application'"),
    resource_id: str | None = Query(None, description="Filter by specific resource ID"),
    from_date: datetime | None = Query(None, description="Start date (inclusive)"),
    to_date: datetime | None = Query(None, description="End date (inclusive)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Return audit log entries with optional filters. Compliance-only."""
    filters = []
    if event_type:
        filters.append(AuditLogModel.event_type.startswith(event_type))
    if actor_id:
        filters.append(AuditLogModel.actor_id == actor_id)
    if resource_type:
        filters.append(AuditLogModel.resource_type == resource_type)
    if resource_id:
        filters.append(AuditLogModel.resource_id == resource_id)
    if from_date:
        filters.append(AuditLogModel.created_at >= from_date)
    if to_date:
        filters.append(AuditLogModel.created_at <= to_date)

    base = select(AuditLogModel)
    if filters:
        base = base.where(and_(*filters))

    total = db.scalar(select(sa_func.count()).select_from(base.subquery()))

    rows = db.scalars(
        base.order_by(desc(AuditLogModel.created_at))
        .offset(offset)
        .limit(limit)
    ).all()

    return AuditLogPage(logs=rows, total=total or 0, limit=limit, offset=offset)


@router.get("/logs/{log_id}", response_model=AuditLogOut)
def get_audit_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Return a single audit log entry by ID."""
    row = db.get(AuditLogModel, log_id)
    if not row:
        raise HTTPException(404, "Audit log entry not found")
    return row
