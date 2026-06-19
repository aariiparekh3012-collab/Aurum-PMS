#!/usr/bin/env python
"""Standalone outbox relay worker.

Continuously polls the transactional outbox table and:
1. Dispatches events to in-process handlers (e.g., provision client)
2. Publishes events to message bus for external consumers
3. Marks events as published only after success (at-least-once delivery)

Usage:
    python scripts/process_outbox.py

    # With custom settings
    OUTBOX_BATCH_SIZE=50 OUTBOX_POLL_INTERVAL=2 python scripts/process_outbox.py

Environment Variables:
    OUTBOX_BATCH_SIZE: Number of events per batch (default: 100)
    OUTBOX_POLL_INTERVAL: Seconds between polls (default: 5)
    OUTBOX_ONE_SHOT: If set, process once and exit (default: run forever)

Docker:
    docker run pms_backend python scripts/process_outbox.py

Kubernetes:
    kubectl apply -f - << 'EOF'
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: pms-outbox-worker
    spec:
      replicas: 1
      template:
        spec:
          containers:
          - name: worker
            image: pms:latest
            command: ["python", "scripts/process_outbox.py"]
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: pms-secrets
                  key: database_url
    EOF
"""
from __future__ import annotations

import os
import signal
import sys
import time

from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.application.client.use_cases.provision_client import ProvisionClientUseCase
from app.infrastructure.db.client_repository import SqlAlchemyClientRepository
from app.infrastructure.db.repositories import SqlAlchemyOnboardingRepository
from app.infrastructure.events.outbox_dispatcher import OutboxDispatcher
from app.infrastructure.events.message_bus import NoOpMessageBus
from app.infrastructure.external.redis_message_bus import RedisMessageBus

log = get_logger("outbox_worker")

# Configuration
BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", "100"))
POLL_INTERVAL = int(os.getenv("OUTBOX_POLL_INTERVAL", "5"))
ONE_SHOT = os.getenv("OUTBOX_ONE_SHOT") is not None

# Global state
RUNNING = True


def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    global RUNNING
    log.info("shutdown_signal_received", signal=signum)
    RUNNING = False


def init_message_bus():
    """Initialize message bus (Redis or no-op fallback)."""
    from app.core.config import get_settings
    settings = get_settings()

    if settings.redis_url:
        try:
            bus = RedisMessageBus()
            if bus.health_check():
                log.info("using_redis_message_bus")
                return bus
        except Exception as e:
            log.warning("redis_initialization_failed", error=str(e))

    log.info("using_noop_message_bus")
    return NoOpMessageBus()


def process_batch() -> int:
    """Process a batch of unpublished outbox events."""
    session = get_session_factory()()
    try:
        # Initialize use cases
        provision = ProvisionClientUseCase(
            SqlAlchemyOnboardingRepository(session),
            SqlAlchemyClientRepository(session),
        )
        message_bus = init_message_bus()
        dispatcher = OutboxDispatcher(session, provision, message_bus)

        # Process batch
        count = dispatcher.process_pending(batch_size=BATCH_SIZE)
        session.commit()

        if count > 0:
            log.info("batch_processed", count=count)

        return count

    except Exception as e:
        log.error("batch_processing_failed", error=str(e))
        session.rollback()
        return 0
    finally:
        session.close()


def run_once() -> int:
    """Process outbox once and exit (for cron jobs / one-off execution)."""
    log.info("outbox_worker_one_shot_mode")
    count = process_batch()
    log.info("outbox_worker_exiting", processed=count)
    return 0 if count >= 0 else 1


def run_forever() -> int:
    """Run worker loop continuously until signaled to stop."""
    log.info(
        "outbox_worker_started",
        batch_size=BATCH_SIZE,
        poll_interval=POLL_INTERVAL,
    )

    processed_total = 0
    poll_count = 0

    while RUNNING:
        try:
            poll_count += 1
            count = process_batch()
            processed_total += count

            if count == 0:
                # No events pending, wait before next poll
                log.debug("no_pending_events", poll_number=poll_count)
                time.sleep(POLL_INTERVAL)
            # If there were events, continue immediately to process more

        except KeyboardInterrupt:
            log.info("keyboard_interrupt_received")
            break
        except Exception as e:
            log.error("worker_error", error=str(e), poll_number=poll_count)
            time.sleep(POLL_INTERVAL)

    log.info(
        "outbox_worker_stopped",
        processed_total=processed_total,
        poll_count=poll_count,
    )
    return 0


def main() -> int:
    """Main entry point."""
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    log.info("outbox_worker_init")

    if ONE_SHOT:
        return run_once()
    else:
        return run_forever()


if __name__ == "__main__":
    sys.exit(main())
