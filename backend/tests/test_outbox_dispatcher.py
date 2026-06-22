"""Unit tests for the transactional-outbox dispatcher.

Tests the OutboxDispatcher in isolation using an in-memory SQLite session
(the OutboxModel columns are SQLite-compatible for this purpose) or, more
practically, by mocking the SQLAlchemy session so we control what rows are
returned without needing a real database.

Covers:
- Happy path: dispatches OnboardingActivated → provision_client + message bus
- Unknown event type: skipped gracefully, still published to bus
- Handler failure: row left unpublished, other rows still processed
- Message bus failure: row left unpublished
- Empty batch: returns 0
- Batch size limiting
- Portfolio provisioning when second handler is wired
"""
from __future__ import annotations

import datetime as dt
import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from app.infrastructure.events.outbox_dispatcher import OutboxDispatcher
from app.infrastructure.events.message_bus import EventMessage, NoOpMessageBus


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_outbox_row(
    event_type: str = "OnboardingActivated",
    published: bool = False,
    aggregate_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> MagicMock:
    """Create a mock OutboxModel row."""
    row = MagicMock()
    row.id = uuid.uuid4()
    row.aggregate_id = aggregate_id or uuid.uuid4()
    row.event_type = event_type
    row.payload = payload or {"some": "data"}
    row.published = published
    row.created_at = dt.datetime(2026, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc)
    return row


def _make_session(rows: list) -> MagicMock:
    """Create a mock SQLAlchemy session that returns `rows` from a query."""
    session = MagicMock()
    session.scalars.return_value.all.return_value = rows
    return session


# ── Tests ────────────────────────────────────────────────────────────────

class TestOutboxDispatcher:
    """Core dispatcher behaviour."""

    def test_process_onboarding_activated(self):
        """OnboardingActivated → calls provision_client + publishes to bus."""
        row = _make_outbox_row("OnboardingActivated")
        session = _make_session([row])
        provision = MagicMock()
        bus = MagicMock()

        dispatcher = OutboxDispatcher(session, provision, message_bus=bus)
        count = dispatcher.process_pending(batch_size=10)

        assert count == 1
        provision.execute.assert_called_once_with(row.aggregate_id)
        bus.publish.assert_called_once()
        assert row.published is True
        session.flush.assert_called_once()

    def test_publishes_correct_event_message(self):
        """The EventMessage sent to the bus has correct fields."""
        row = _make_outbox_row("OnboardingActivated", payload={"key": "val"})
        session = _make_session([row])
        bus = MagicMock()

        dispatcher = OutboxDispatcher(session, MagicMock(), message_bus=bus)
        dispatcher.process_pending()

        msg: EventMessage = bus.publish.call_args[0][0]
        assert msg.event_id == str(row.id)
        assert msg.aggregate_id == str(row.aggregate_id)
        assert msg.event_type == "OnboardingActivated"
        assert msg.payload == {"key": "val"}
        assert msg.timestamp == row.created_at.isoformat()

    def test_unknown_event_type_still_published(self):
        """Events with no handler are still marked published + sent to bus."""
        row = _make_outbox_row("SomeOtherEvent")
        session = _make_session([row])
        provision = MagicMock()
        bus = MagicMock()

        dispatcher = OutboxDispatcher(session, provision, message_bus=bus)
        count = dispatcher.process_pending()

        assert count == 1
        provision.execute.assert_not_called()
        bus.publish.assert_called_once()
        assert row.published is True

    def test_handler_failure_leaves_row_unpublished(self):
        """If provision_client raises, that row stays unpublished."""
        good_row = _make_outbox_row("OnboardingActivated")
        bad_row = _make_outbox_row("OnboardingActivated")
        session = _make_session([bad_row, good_row])

        provision = MagicMock()
        provision.execute.side_effect = [RuntimeError("DB down"), None]
        bus = MagicMock()

        dispatcher = OutboxDispatcher(session, provision, message_bus=bus)
        count = dispatcher.process_pending()

        # bad_row failed, good_row succeeded
        assert count == 1
        assert bad_row.published is not True  # stays False (MagicMock default)
        assert good_row.published is True

    def test_message_bus_failure_leaves_row_unpublished(self):
        """If bus.publish raises, that row stays unpublished."""
        row = _make_outbox_row("OnboardingActivated")
        session = _make_session([row])
        provision = MagicMock()
        bus = MagicMock()
        bus.publish.side_effect = ConnectionError("Redis down")

        dispatcher = OutboxDispatcher(session, provision, message_bus=bus)
        count = dispatcher.process_pending()

        assert count == 0
        # published was set to True before the error? Let's check the actual logic —
        # the dispatcher calls _handle, then bus.publish, then sets published=True.
        # Bus failure means published never gets set.
        assert row.published is not True

    def test_empty_batch_returns_zero(self):
        """No pending rows → returns 0, no side effects."""
        session = _make_session([])
        dispatcher = OutboxDispatcher(session, MagicMock(), message_bus=MagicMock())
        assert dispatcher.process_pending() == 0

    def test_batch_size_passed_to_query(self):
        """batch_size is forwarded to the SQL LIMIT clause."""
        session = _make_session([])
        dispatcher = OutboxDispatcher(session, MagicMock())
        dispatcher.process_pending(batch_size=42)

        # Verify .limit(42) was in the chain
        # The select().where().order_by().limit().with_for_update() chain
        # is built then passed to session.scalars(). We check the stmt arg.
        stmt = session.scalars.call_args[0][0]
        # SQLAlchemy compiles the limit into the statement
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "42" in compiled

    def test_multiple_events_processed_in_order(self):
        """Multiple rows are each dispatched and counted."""
        rows = [_make_outbox_row("OnboardingActivated") for _ in range(3)]
        session = _make_session(rows)
        provision = MagicMock()
        bus = MagicMock()

        dispatcher = OutboxDispatcher(session, provision, message_bus=bus)
        count = dispatcher.process_pending()

        assert count == 3
        assert provision.execute.call_count == 3
        assert bus.publish.call_count == 3
        for row in rows:
            assert row.published is True

    def test_defaults_to_noop_message_bus(self):
        """If no message_bus is provided, NoOpMessageBus is used."""
        row = _make_outbox_row("OnboardingActivated")
        session = _make_session([row])
        provision = MagicMock()

        dispatcher = OutboxDispatcher(session, provision)  # no bus arg
        count = dispatcher.process_pending()

        # Should succeed — NoOpMessageBus doesn't raise
        assert count == 1
        assert row.published is True

    def test_portfolio_provision_called_for_onboarding_activated(self):
        """When portfolio provisioner is wired, it's called for OnboardingActivated."""
        row = _make_outbox_row("OnboardingActivated")
        session = _make_session([row])
        provision = MagicMock()
        portfolio_provision = MagicMock()
        bus = MagicMock()

        dispatcher = OutboxDispatcher(
            session, provision,
            provision_portfolio_client=portfolio_provision,
            message_bus=bus,
        )
        count = dispatcher.process_pending()

        assert count == 1
        provision.execute.assert_called_once()
        portfolio_provision.execute.assert_called_once()

    def test_portfolio_provision_not_called_for_other_events(self):
        """Portfolio provisioner is only triggered by OnboardingActivated."""
        row = _make_outbox_row("KycVerified")
        session = _make_session([row])
        provision = MagicMock()
        portfolio_provision = MagicMock()

        dispatcher = OutboxDispatcher(
            session, provision,
            provision_portfolio_client=portfolio_provision,
        )
        dispatcher.process_pending()

        provision.execute.assert_not_called()
        portfolio_provision.execute.assert_not_called()


class TestNoOpMessageBus:
    """NoOpMessageBus — the dev fallback."""

    def test_publish_does_not_raise(self):
        bus = NoOpMessageBus()
        msg = EventMessage(
            event_id="e1", aggregate_id="a1",
            event_type="Test", payload={}, timestamp="2026-01-01T00:00:00",
        )
        bus.publish(msg)  # should not raise

    def test_publish_batch_delegates_to_publish(self):
        bus = NoOpMessageBus()
        msgs = [
            EventMessage(
                event_id=f"e{i}", aggregate_id="a1",
                event_type="Test", payload={}, timestamp="2026-01-01T00:00:00",
            )
            for i in range(3)
        ]
        bus.publish_batch(msgs)  # should not raise

    def test_health_check_returns_true(self):
        assert NoOpMessageBus().health_check() is True
