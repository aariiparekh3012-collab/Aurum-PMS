"""Notifications & activity feed endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, func, update
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models_notifications import ActivityLogModel

router = APIRouter(prefix="/notifications", tags=["notifications"])


# -- Schemas -----------------------------------------------------------------

class ActivityOut(BaseModel):
    id: uuid.UUID
    actor_role: str
    actor_subject: str
    action: str
    entity_type: str
    entity_id: str | None = None
    detail: str | None = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: str | None = None
    detail: str | None = None


class FeedResponse(BaseModel):
    items: list[ActivityOut]
    total: int
    unread: int


class UnreadCount(BaseModel):
    count: int


# -- Helpers -----------------------------------------------------------------

def _user_scope_filter(user: dict):
    """Staff (compliance/RM) see all activity; investors see only their own."""
    role = user.get("role")
    if role in ("compliance", "relationship_manager"):
        return None  # no extra filter
    sub = user.get("sub", "")
    return ActivityLogModel.actor_subject == sub


# -- Endpoints ---------------------------------------------------------------

@router.get("/feed", response_model=FeedResponse)
def activity_feed(
    entity_type: str | None = Query(None),
    limit: int = Query(30, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    """Paginated activity feed, scoped to the requesting user's visibility."""
    base = select(ActivityLogModel)
    scope = _user_scope_filter(user)
    if scope is not None:
        base = base.where(scope)
    if entity_type:
        base = base.where(ActivityLogModel.entity_type == entity_type)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    items = db.scalars(
        base.order_by(desc(ActivityLogModel.created_at))
        .offset(offset)
        .limit(limit)
    ).all()

    unread_q = (
        select(func.count())
        .select_from(ActivityLogModel)
        .where(ActivityLogModel.is_read.is_(False))
    )
    if scope is not None:
        unread_q = unread_q.where(scope)
    unread = db.scalar(unread_q) or 0

    return FeedResponse(items=items, total=total, unread=unread)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    q = (
        select(func.count())
        .select_from(ActivityLogModel)
        .where(ActivityLogModel.is_read.is_(False))
    )
    scope = _user_scope_filter(user)
    if scope is not None:
        q = q.where(scope)
    count = db.scalar(q) or 0
    return UnreadCount(count=count)


@router.post("/log", response_model=ActivityOut, status_code=201)
def log_activity(
    body: ActivityCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(deps.require_staff),
):
    """Log a new activity event. Staff only."""
    entry = ActivityLogModel(
        actor_role=user.get("role", "system"),
        actor_subject=user.get("sub", "system"),
        action=body.action,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        detail=body.detail,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/mark-read")
def mark_all_read(
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    """Mark all of the requesting user's notifications as read."""
    stmt = (
        update(ActivityLogModel)
        .where(ActivityLogModel.is_read.is_(False))
    )
    scope = _user_scope_filter(user)
    if scope is not None:
        stmt = stmt.where(scope)
    db.execute(stmt.values(is_read=True))
    db.commit()
    return {"status": "ok"}


@router.post("/mark-read/{activity_id}")
def mark_one_read(
    activity_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    entry = db.get(ActivityLogModel, activity_id)
    if entry:
        # Investors can only mark their own notifications
        scope = _user_scope_filter(user)
        if scope is not None and entry.actor_subject != user.get("sub", ""):
            return {"status": "ok"}  # silently ignore — don't reveal existence
        entry.is_read = True
        db.commit()
    return {"status": "ok"}
