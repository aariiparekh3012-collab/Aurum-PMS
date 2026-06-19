"""Use case: provision a client record when onboarding reaches ACTIVE."""
from __future__ import annotations
import uuid
from app.application.portfolio.dto import ClientView, ProvisionClientCommand
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import hash_pan
from app.domain.onboarding.repositories import OnboardingRepository
from app.domain.portfolio.entities import Client
from app.domain.portfolio.repositories import ClientRepository


class ProvisionClientUseCase:
    def __init__(self, onboarding_repo: OnboardingRepository, client_repo: ClientRepository):
        self._onboarding = onboarding_repo
        self._clients = client_repo

    def execute(self, cmd: ProvisionClientCommand) -> ClientView:
        app = self._onboarding.get(cmd.onboarding_application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")
        if app.status.value != "active":
            raise ValidationError("Application must be active to provision client", code="not_active")

        existing = self._clients.get_by_onboarding_id(cmd.onboarding_application_id)
        if existing:
            raise ValidationError("Client already provisioned for this application", code="already_provisioned")

        client_code = f"PMS-{uuid.uuid4().hex[:8].upper()}"
        client = Client.provision(
            onboarding_application_id=cmd.onboarding_application_id,
            client_code=client_code,
            pan_hash=hash_pan(app.pan.value),
            investor_type=app.investor_type.value,
            full_name=app.full_name,
            email=app.email,
        )
        self._clients.add(client)
        return ClientView(
            id=client.id, client_code=client.client_code,
            full_name=client.full_name, email=client.email,
            investor_type=client.investor_type, status=client.status.value,
        )
