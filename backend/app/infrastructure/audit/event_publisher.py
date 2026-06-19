"""Transactional-outbox EventPublisher implementing the application port.

Events are written to the `event_outbox` table inside the SAME DB transaction as
the aggregate change, guaranteeing at-least-once delivery without 2-phase commit.
A separate relay process polls the outbox and pushes to the message bus.
"""
from __future__ import annotations

import dataclasses
import datetime as dt

from sqlalchemy.orm import Session

from app.application.onboarding.ports import EventPublisher
from app.infrastructure.db.models import OutboxModel


class OutboxEventPublisher(EventPublisher):
    def __init__(self, session: Session) -> None:
        self._s = session

    def publish(self, events: list) -> None:
        for event in events:
            self._s.add(
                OutboxModel(
                    aggregate_id=event.aggregate_id,
                    event_type=type(event).__name__,
                    payload={
                        k: (v.isoformat() if isinstance(v, dt.datetime) else str(v))
                        for k, v in dataclasses.asdict(event).items()
                    },
                    created_at=dt.datetime.now(dt.timezone.utc),
                )
            )
        self._s.flush()
