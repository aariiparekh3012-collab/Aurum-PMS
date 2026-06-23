"""Messaging endpoints — role-scoped conversations & messages.

Permission matrix:
  admin       → can message anyone
  rm          → investor, compliance, admin
  investor    → rm, admin
  compliance  → rm, admin
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.infrastructure.db.models_auth import UserModel
from app.infrastructure.db.models_messaging import (
    ConversationModel,
    ConversationParticipantModel,
    MessageModel,
)

router = APIRouter(prefix="/messages", tags=["messaging"])

# ── Role permission matrix ───────────────────────────────────────────────────

_CAN_MESSAGE: dict[str, set[str]] = {
    "admin": {"admin", "rm", "relationship_manager", "investor", "compliance"},
    "rm": {"investor", "admin", "compliance"},
    "relationship_manager": {"investor", "admin", "compliance"},
    "investor": {"rm", "relationship_manager", "admin"},
    "compliance": {"rm", "relationship_manager", "admin"},
}


def _can_message(sender_role: str, recipient_role: str) -> bool:
    allowed = _CAN_MESSAGE.get(sender_role, set())
    return recipient_role in allowed


# ── Schemas ──────────────────────────────────────────────────────────────────

class ContactOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: uuid.UUID
    participants: list[ContactOut]
    last_message: MessageOut | None = None
    unread_count: int = 0
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(BaseModel):
    id: uuid.UUID
    participants: list[ContactOut]
    messages: list[MessageOut]

    class Config:
        from_attributes = True


class NewMessageBody(BaseModel):
    body: str


class NewConversationBody(BaseModel):
    recipient_id: uuid.UUID
    body: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_user(db: Session, user_jwt: dict) -> UserModel:
    """Resolve the JWT subject to a UserModel. JWT sub is the user's email."""
    sub = user_jwt.get("sub", "")
    u = db.scalar(select(UserModel).where(UserModel.email == sub))
    if not u:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User not found")
    return u


def _find_existing_dm(db: Session, user_a_id: uuid.UUID, user_b_id: uuid.UUID):
    """Find an existing 1:1 conversation between two users."""
    subq = (
        select(ConversationParticipantModel.conversation_id)
        .where(ConversationParticipantModel.user_id.in_([user_a_id, user_b_id]))
        .group_by(ConversationParticipantModel.conversation_id)
        .having(func.count(ConversationParticipantModel.user_id) == 2)
    ).subquery()
    # Also ensure the conversation has exactly 2 participants total
    conv_id = db.scalar(
        select(ConversationParticipantModel.conversation_id)
        .where(ConversationParticipantModel.conversation_id.in_(select(subq)))
        .group_by(ConversationParticipantModel.conversation_id)
        .having(func.count() == 2)
    )
    return conv_id


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List users the caller is allowed to message."""
    me = _resolve_user(db, user)
    allowed_roles = _CAN_MESSAGE.get(me.role, set())
    if not allowed_roles:
        return []
    contacts = db.scalars(
        select(UserModel)
        .where(UserModel.is_active.is_(True))
        .where(UserModel.id != me.id)
        .where(UserModel.role.in_(allowed_roles))
        .order_by(UserModel.full_name)
    ).all()
    return contacts


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all conversations for the current user, newest first."""
    me = _resolve_user(db, user)

    # Get conversation IDs the user participates in
    my_conv_ids = select(ConversationParticipantModel.conversation_id).where(
        ConversationParticipantModel.user_id == me.id
    )

    convs = db.scalars(
        select(ConversationModel)
        .where(ConversationModel.id.in_(my_conv_ids))
        .options(joinedload(ConversationModel.participants))
        .order_by(desc(ConversationModel.updated_at))
    ).unique().all()

    result = []
    for conv in convs:
        # Get participant info
        participant_ids = [p.user_id for p in conv.participants]
        users_map = {
            u.id: u
            for u in db.scalars(
                select(UserModel).where(UserModel.id.in_(participant_ids))
            ).all()
        }

        participants = [
            ContactOut(
                id=u.id, full_name=u.full_name, email=u.email, role=u.role
            )
            for u in users_map.values()
        ]

        # Last message
        last_msg_row = db.scalar(
            select(MessageModel)
            .where(MessageModel.conversation_id == conv.id)
            .order_by(desc(MessageModel.created_at))
            .limit(1)
        )
        last_message = None
        if last_msg_row:
            sender = users_map.get(last_msg_row.sender_id)
            last_message = MessageOut(
                id=last_msg_row.id,
                sender_id=last_msg_row.sender_id,
                sender_name=sender.full_name if sender else "Unknown",
                body=last_msg_row.body,
                created_at=last_msg_row.created_at,
            )

        # Unread count
        my_participant = next(
            (p for p in conv.participants if p.user_id == me.id), None
        )
        unread = 0
        if my_participant:
            unread_q = (
                select(func.count())
                .select_from(MessageModel)
                .where(MessageModel.conversation_id == conv.id)
                .where(MessageModel.sender_id != me.id)
            )
            if my_participant.last_read_at:
                unread_q = unread_q.where(
                    MessageModel.created_at > my_participant.last_read_at
                )
            unread = db.scalar(unread_q) or 0

        result.append(
            ConversationOut(
                id=conv.id,
                participants=participants,
                last_message=last_message,
                unread_count=unread,
                updated_at=conv.updated_at,
            )
        )

    return result


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: uuid.UUID,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get messages in a conversation. Marks messages as read."""
    me = _resolve_user(db, user)

    # Verify participation
    participant = db.scalar(
        select(ConversationParticipantModel).where(
            and_(
                ConversationParticipantModel.conversation_id == conversation_id,
                ConversationParticipantModel.user_id == me.id,
            )
        )
    )
    if not participant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    # Mark as read
    participant.last_read_at = datetime.now(timezone.utc)

    # Get participants
    all_participants = db.scalars(
        select(ConversationParticipantModel).where(
            ConversationParticipantModel.conversation_id == conversation_id
        )
    ).all()
    user_ids = [p.user_id for p in all_participants]
    users_map = {
        u.id: u
        for u in db.scalars(
            select(UserModel).where(UserModel.id.in_(user_ids))
        ).all()
    }

    participants = [
        ContactOut(id=u.id, full_name=u.full_name, email=u.email, role=u.role)
        for u in users_map.values()
    ]

    # Get messages
    messages_rows = db.scalars(
        select(MessageModel)
        .where(MessageModel.conversation_id == conversation_id)
        .order_by(MessageModel.created_at)
        .offset(offset)
        .limit(limit)
    ).all()

    messages = [
        MessageOut(
            id=m.id,
            sender_id=m.sender_id,
            sender_name=users_map[m.sender_id].full_name
            if m.sender_id in users_map
            else "Unknown",
            body=m.body,
            created_at=m.created_at,
        )
        for m in messages_rows
    ]

    return ConversationDetailOut(
        id=conversation_id, participants=participants, messages=messages
    )


@router.post("/conversations", response_model=ConversationDetailOut, status_code=201)
def start_conversation(
    body: NewConversationBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Start a new conversation (or reuse existing DM) with a user."""
    me = _resolve_user(db, user)
    recipient = db.get(UserModel, body.recipient_id)
    if not recipient or not recipient.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipient not found")

    # Permission check
    if not _can_message(me.role, recipient.role):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Your role ({me.role}) cannot message {recipient.role} users",
        )

    # Reuse existing DM if one exists
    existing = _find_existing_dm(db, me.id, recipient.id)
    if existing:
        conv_id = existing
        conv = db.get(ConversationModel, conv_id)
    else:
        conv = ConversationModel()
        db.add(conv)
        db.flush()

        db.add(ConversationParticipantModel(conversation_id=conv.id, user_id=me.id))
        db.add(
            ConversationParticipantModel(
                conversation_id=conv.id, user_id=recipient.id
            )
        )
        db.flush()

    # Add the message
    now = datetime.now(timezone.utc)
    msg = MessageModel(
        conversation_id=conv.id, sender_id=me.id, body=body.body.strip()
    )
    db.add(msg)
    conv.updated_at = now

    # Mark sender's participation as read
    my_participant = db.scalar(
        select(ConversationParticipantModel).where(
            and_(
                ConversationParticipantModel.conversation_id == conv.id,
                ConversationParticipantModel.user_id == me.id,
            )
        )
    )
    if my_participant:
        my_participant.last_read_at = now

    db.flush()

    # Build response
    users_map = {me.id: me, recipient.id: recipient}
    participants = [
        ContactOut(id=u.id, full_name=u.full_name, email=u.email, role=u.role)
        for u in users_map.values()
    ]

    return ConversationDetailOut(
        id=conv.id,
        participants=participants,
        messages=[
            MessageOut(
                id=msg.id,
                sender_id=msg.sender_id,
                sender_name=me.full_name,
                body=msg.body,
                created_at=msg.created_at or now,
            )
        ],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=201,
)
def send_message(
    conversation_id: uuid.UUID,
    body: NewMessageBody,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Send a message in an existing conversation."""
    me = _resolve_user(db, user)

    participant = db.scalar(
        select(ConversationParticipantModel).where(
            and_(
                ConversationParticipantModel.conversation_id == conversation_id,
                ConversationParticipantModel.user_id == me.id,
            )
        )
    )
    if not participant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

    now = datetime.now(timezone.utc)
    msg = MessageModel(
        conversation_id=conversation_id, sender_id=me.id, body=body.body.strip()
    )
    db.add(msg)

    # Update conversation timestamp
    conv = db.get(ConversationModel, conversation_id)
    if conv:
        conv.updated_at = now

    # Mark as read for sender
    participant.last_read_at = now
    db.flush()

    return MessageOut(
        id=msg.id,
        sender_id=msg.sender_id,
        sender_name=me.full_name,
        body=msg.body,
        created_at=msg.created_at or now,
    )


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Total unread message count across all conversations."""
    me = _resolve_user(db, user)

    my_participations = db.scalars(
        select(ConversationParticipantModel).where(
            ConversationParticipantModel.user_id == me.id
        )
    ).all()

    total_unread = 0
    for p in my_participations:
        q = (
            select(func.count())
            .select_from(MessageModel)
            .where(MessageModel.conversation_id == p.conversation_id)
            .where(MessageModel.sender_id != me.id)
        )
        if p.last_read_at:
            q = q.where(MessageModel.created_at > p.last_read_at)
        total_unread += db.scalar(q) or 0

    return {"count": total_unread}
