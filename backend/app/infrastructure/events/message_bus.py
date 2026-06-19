"""Message bus abstraction for publishing domain events.

The outbox relay publishes to a message bus for downstream consumers
(e.g., portfolio provisioning service, compliance dashboard, analytics).

This is a PORT (abstract interface); concrete implementations (Redis, RabbitMQ, SQS)
live in infrastructure/external/.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EventMessage:
    """An event message ready for publishing to the bus."""

    event_id: str  # UUID from OutboxModel.id
    aggregate_id: str  # Application ID
    event_type: str  # OnboardingActivated, KycVerified, etc.
    payload: dict  # Event data (JSON-serializable)
    timestamp: str  # ISO8601


class MessageBusPort(ABC):
    """Publish domain events to a message bus for async consumers."""

    @abstractmethod
    def publish(self, message: EventMessage) -> None:
        """Publish a single event message.

        Args:
            message: EventMessage to publish

        Raises:
            Exception: If publishing fails (will be retried by outbox relay)
        """

    @abstractmethod
    def publish_batch(self, messages: list[EventMessage]) -> None:
        """Publish multiple event messages (optimization for bulk operations)."""

    @abstractmethod
    def health_check(self) -> bool:
        """Check if message bus is reachable. Return True if healthy."""


class NoOpMessageBus(MessageBusPort):
    """No-op implementation for local dev (logs instead of publishing)."""

    def __init__(self) -> None:
        from app.core.logging import get_logger
        self._log = get_logger("message_bus")

    def publish(self, message: EventMessage) -> None:
        self._log.debug(
            "event_published_noop",
            event_id=message.event_id,
            event_type=message.event_type,
            aggregate_id=message.aggregate_id,
        )

    def publish_batch(self, messages: list[EventMessage]) -> None:
        for msg in messages:
            self.publish(msg)

    def health_check(self) -> bool:
        return True
