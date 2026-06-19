"""Use case: retrieve an application by ID or list by status."""
from __future__ import annotations

import uuid

from app.application.onboarding.dto import ApplicationView
from app.application.onboarding.mappers import to_view
from app.core.exceptions import NotFoundError
from app.domain.onboarding.enums import OnboardingStatus
from app.domain.onboarding.repositories import OnboardingRepository


class GetApplicationUseCase:
    def __init__(self, repo: OnboardingRepository) -> None:
        self._repo = repo

    def get(self, application_id: uuid.UUID) -> ApplicationView:
        app = self._repo.get(application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")
        return to_view(app)

    def list_by_status(
        self, status: str, *, offset: int = 0, limit: int = 50,
    ) -> list[ApplicationView]:
        s = OnboardingStatus(status)
        apps = self._repo.list_by_status(s, offset=offset, limit=limit)
        return [to_view(a) for a in apps]
