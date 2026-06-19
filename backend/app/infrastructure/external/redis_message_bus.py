"""Redis Pub/Sub implementation of MessageBusPort.

Publishes domain events to Redis channels for downstream consumers to subscribe.
Each event type has its own channel (e.g., onboarding.activated, kyc.verified).
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import redis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.events.message_bus import EventMessage, MessageBusPort

if TYPE_CHECKING:
    from redis.client import Redis

log = get_logger("redis_message_bus")


class RedisMessageBus(MessageBusPort):
    """Publishes events to Redis Pub/Sub channels."""

    def __init__(self, redis_client: Redis | None = None) -> None:
        if redis_client:
            self._redis = redis_client
        else:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    9: 3,  # TCP_KEEPCNT
                },
            )
        log.info("Redis message bus initialized")

    def publish(self, message: EventMessage) -> None:
        """Publish a single event to a channel named after the event type."""
        channel = self._get_channel_name(message.event_type)
        payload = json.dumps(
            {
                "event_id": message.event_id,
                "aggregate_id": message.aggregate_id,
                "event_type": message.event_type,
                "payload": message.payload,
                "timestamp": message.timestamp,
            }
        )
        try:
            subscribers = self._redis.publish(channel, payload)
            log.info(
                "event_published",
                event_id=message.event_id,
                event_type=message.event_type,
                channel=channel,
                subscribers=subscribers,
            )
        except Exception as e:
            log.error(
                "event_publish_failed",
                event_id=message.event_id,
                event_type=message.event_type,
                error=str(e),
            )
            raise

    def publish_batch(self, messages: list[EventMessage]) -> None:
        """Publish multiple messages efficiently."""
        # Use pipeline for atomicity
        pipe = self._redis.pipeline()
        for message in messages:
            channel = self._get_channel_name(message.event_type)
            payload = json.dumps(
                {
                    "event_id": message.event_id,
                    "aggregate_id": message.aggregate_id,
                    "event_type": message.event_type,
                    "payload": message.payload,
                    "timestamp": message.timestamp,
                }
            )
            pipe.publish(channel, payload)
        try:
            results = pipe.execute()
            log.info("batch_published", count=len(messages), results=results)
        except Exception as e:
            log.error("batch_publish_failed", count=len(messages), error=str(e))
            raise

    def health_check(self) -> bool:
        """Check if Redis is reachable."""
        try:
            self._redis.ping()
            return True
        except Exception as e:
            log.error("redis_health_check_failed", error=str(e))
            return False

    @staticmethod
    def _get_channel_name(event_type: str) -> str:
        """Convert event type to channel name (e.g., OnboardingActivated -> onboarding.activated)."""
        # OnboardingActivated -> onboarding.activated
        # KycVerified -> kyc.verified
        import re

        # Insert dots before capital letters and convert to lowercase
        channel = re.sub(r"(?<!^)(?=[A-Z])", ".", event_type)
        return channel.lower()
