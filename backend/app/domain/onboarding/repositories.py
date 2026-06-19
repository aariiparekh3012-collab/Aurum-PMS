"""Repository port — the domain's interface for persistence."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import OnboardingStatus


class OnboardingRepository(ABC):
    @abstractmethod
    def add(self, application: OnboardingApplication) -> None: ...

    @abstractmethod
    def get(self, application_id: uuid.UUID) -> OnboardingApplication | None: ...

    @abstractmethod
    def get_by_pan(self, pan: str) -> OnboardingApplication | None: ...

    @abstractmethod
    def update(self, application: OnboardingApplication) -> None: ...

    @abstractmethod
    def list_by_status(
        self, status: OnboardingStatus, *, offset: int = 0, limit: int = 50,
    ) -> list[OnboardingApplication]: ...

    @abstractmethod
    def count_by_status(self, status: OnboardingStatus) -> int: ...
