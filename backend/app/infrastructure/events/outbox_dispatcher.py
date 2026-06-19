"""Transactional-outbox dispatcher (relay).

Polls `event_outbox` for unpublished events and:
1. Dispatches to in-process handlers (e.g., provision client)
2. Publishes to message bus for external subscribers
3. Marks published only after all handlers succeed (at-least-once delivery)

Handlers must be idempotent (all are, by design).

The dispatcher runs as part of the main request (sync) or as a standalone
worker process (process_outbox.py).
"""
from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.client.use_cases.provision_client import ProvisionClientUseCase
from app.core.logging import get_logger
from app.infrastructure.db.models import OutboxModel
from app.infrastructure.events.message_bus import EventMessage, MessageBusPort, NoOpMessageBus

if TYPE_CHECKING:
    from app.application.portfolio.use_cases.provision_client import (
        ProvisionClientUseCase as PortfolioProvisionClientUseCase,
    )
    from app.application.portfolio.dto import ProvisionClientCommand

log = get_logger("outbox")


class OutboxDispatcher:
    """Dispatches events from the transactional outbox."""

    def __init__(
        self,
        session: Session,
        provision_client: ProvisionClientUseCase,
        provision_portfolio_client: "PortfolioProvisionClientUseCase | None" = None,
        message_bus: MessageBusPort | None = None,
    ) -> None:
        self._s = session
        self._provision_client = provision_client
        self._provision_portfolio_client = provision_portfolio_client
        self._message_bus = message_bus or NoOpMessageBus()

    def process_pending(self, *, batch_size: int = 100) -> int:
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.published.is_(False))
            .order_by(OutboxModel.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        rows = self._s.scalars(stmt).all()
        processed = 0

        for row in rows:
            try:
                self._handle(row)

                message = EventMessage(
                    event_id=str(row.id),
                    aggregate_id=str(row.aggregate_id),
                    event_type=row.event_type,
                    payload=row.payload or {},
                    timestamp=row.created_at.isoformat(),
                )
                self._message_bus.publish(message)

                row.published = True
                processed += 1

                log.info(
                    "event_processed",
                    event_id=str(row.id),
                    event_type=row.event_type,
                    aggregate_id=str(row.aggregate_id),
                )

            except Exception as exc:
                log.error(
                    "outbox_processing_failed",
                    event_id=str(row.id),
                    event_type=row.event_type,
                    error=str(exc),
                )

        self._s.flush()
        return processed

    def _handle(self, row: OutboxModel) -> None:
        if row.event_type == "OnboardingActivated":
            log.debug(
                "dispatching_handler",
                event_type=row.event_type,
                handler="provision_client",
            )
            self._provision_client.execute(row.aggregate_id)
            if self._provision_portfolio_client is not None:
                from app.application.portfolio.dto import ProvisionClientCommand
                log.debug(
                    "dispatching_handler",
                    event_type=row.event_type,
                    handler="provision_portfolio_client",
                )
                self._provision_portfolio_client.execute(
                    ProvisionClientCommand(onboarding_application_id=row.aggregate_id)
                )
        else:
            log.debug("outbox_event_unhandled", event_type=row.event_type)
