"""Use case: confirm eSign — fetches result from the eSign provider and transitions the aggregate."""
from __future__ import annotations

import uuid

from app.application.onboarding.dto import ApplicationView
from app.application.onboarding.mappers import to_view
from app.application.onboarding.ports import EsignPort, EventPublisher
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.onboarding.repositories import OnboardingRepository


class ConfirmEsignUseCase:
    def __init__(
        self, repo: OnboardingRepository, esign: EsignPort, publisher: EventPublisher,
    ) -> None:
        self._repo = repo
        self._esign = esign
        self._publisher = publisher

    def execute(self, application_id: uuid.UUID, transaction_id: str) -> ApplicationView:
        app = self._repo.get(application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")

        result = self._esign.fetch_result(transaction_id=transaction_id)
        if not result.signed:
            raise ValidationError("eSign not yet completed", code="esign_pending")

        app.mark_agreement_signed(esign_reference=result.reference)
        self._repo.update(app)
        self._publisher.publish(app.pull_events())
        return to_view(app)
