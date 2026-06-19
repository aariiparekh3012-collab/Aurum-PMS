"""Use-case tests for CreateApplicationUseCase with in-memory fakes."""
from __future__ import annotations

import uuid
import pytest

from app.application.onboarding.dto import CreateApplicationCommand
from app.application.onboarding.use_cases.create_application import CreateApplicationUseCase
from app.core.exceptions import ValidationError
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import OnboardingStatus
from app.domain.onboarding.repositories import OnboardingRepository


# ── In-memory fakes ──────────────────────────────────────────────────────

class FakeEventPublisher:
    def __init__(self):
        self.events: list = []
    def publish(self, events: list) -> None:
        self.events.extend(events)


class InMemoryOnboardingRepository(OnboardingRepository):
    def __init__(self):
        self._store: dict[uuid.UUID, OnboardingApplication] = {}
        self._pan_index: dict[str, uuid.UUID] = {}

    def add(self, app: OnboardingApplication) -> None:
        self._store[app.id] = app
        self._pan_index[app.pan.value.upper()] = app.id

    def get(self, application_id: uuid.UUID) -> OnboardingApplication | None:
        return self._store.get(application_id)

    def get_by_pan(self, pan: str) -> OnboardingApplication | None:
        aid = self._pan_index.get(pan.upper())
        return self._store.get(aid) if aid else None

    def update(self, app: OnboardingApplication) -> None:
        self._store[app.id] = app

    def list_by_status(self, status, *, offset=0, limit=50):
        return [a for a in self._store.values() if a.status == status][offset:offset+limit]

    def count_by_status(self, status) -> int:
        return sum(1 for a in self._store.values() if a.status == status)


# ── Tests ────────────────────────────────────────────────────────────────

def _make_uc():
    repo = InMemoryOnboardingRepository()
    pub = FakeEventPublisher()
    uc = CreateApplicationUseCase(repo, pub)
    return uc, repo, pub


def _cmd(**overrides):
    defaults = dict(
        investor_type="individual", full_name="Asha Rao", email="asha@example.com",
        mobile="9876543210", pan="ABCDE1234F", proposed_investment_inr=5_000_000.0,
    )
    defaults.update(overrides)
    return CreateApplicationCommand(**defaults)


def test_create_application_success():
    uc, repo, pub = _make_uc()
    view = uc.execute(_cmd())
    assert view.status == "draft"
    assert view.full_name == "Asha Rao"
    assert len(pub.events) == 1


def test_create_application_duplicate_pan_rejected():
    uc, repo, pub = _make_uc()
    uc.execute(_cmd())
    with pytest.raises(ValidationError, match="already exists"):
        uc.execute(_cmd(email="other@example.com"))


def test_create_below_minimum_rejected():
    uc, _, _ = _make_uc()
    with pytest.raises(ValidationError, match="below SEBI minimum"):
        uc.execute(_cmd(proposed_investment_inr=1_000_000.0))
