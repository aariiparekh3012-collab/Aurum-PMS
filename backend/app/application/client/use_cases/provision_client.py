"""Use case: provision a Client Master record from a completed onboarding.

Triggered by the `OnboardingActivated` domain event (via the outbox dispatcher) or
callable directly. It reads the onboarding application (read-only — onboarding code
is unchanged), maps it to a Client, and persists it.

Idempotent: re-running for the same onboarding application returns the existing
client instead of creating a duplicate.
"""
from __future__ import annotations

import uuid

from app.application.client.dto import ClientView
from app.application.client.mappers import to_view
from app.core.exceptions import InvalidStateTransition, NotFoundError
from app.domain.client.entities import Client
from app.domain.client.repositories import ClientRepository
from app.domain.onboarding.enums import OnboardingStatus
from app.domain.onboarding.repositories import OnboardingRepository


def _generate_client_code() -> str:
    return f"CL-{uuid.uuid4().hex[:8].upper()}"


class ProvisionClientUseCase:
    def __init__(
        self,
        onboarding_repo: OnboardingRepository,
        client_repo: ClientRepository,
    ) -> None:
        self._onboarding = onboarding_repo
        self._clients = client_repo

    def execute(self, application_id: uuid.UUID) -> ClientView:
        # Idempotency: already provisioned?
        existing = self._clients.get_by_onboarding_application_id(application_id)
        if existing is not None:
            return to_view(existing)

        app = self._onboarding.get(application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")
        if app.status is not OnboardingStatus.ACTIVE:
            raise InvalidStateTransition(
                f"Cannot provision client: onboarding status is {app.status.value}, "
                "expected active"
            )

        client = Client.from_onboarding(
            application_id=app.id,
            client_code=_generate_client_code(),
            pan=app.pan,
            investor_type=app.investor_type,
            full_name=app.full_name,
            email=app.email,
            mobile=app.mobile,
            bank_account=app.bank_account,
            demat_account=app.demat_account,
            risk_category=app.risk_category,
            risk_score=app.risk_score,
        )
        self._clients.add(client)
        return to_view(client)
