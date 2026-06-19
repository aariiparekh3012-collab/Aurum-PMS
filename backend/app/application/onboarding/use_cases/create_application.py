"""Use case: create a new onboarding application (DRAFT)."""
from __future__ import annotations

from app.application.onboarding.dto import ApplicationView, CreateApplicationCommand
from app.application.onboarding.mappers import to_view
from app.application.onboarding.ports import EventPublisher
from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import InvestorType
from app.domain.onboarding.repositories import OnboardingRepository
from app.domain.onboarding.value_objects import PAN, Money


class CreateApplicationUseCase:
    def __init__(self, repo: OnboardingRepository, publisher: EventPublisher) -> None:
        self._repo = repo
        self._publisher = publisher
        self._settings = get_settings()

    def execute(self, cmd: CreateApplicationCommand) -> ApplicationView:
        pan = PAN(cmd.pan.upper())

        if self._repo.get_by_pan(pan.value):
            raise ValidationError(
                "An application already exists for this PAN", code="duplicate_pan"
            )

        application = OnboardingApplication.create(
            investor_type=InvestorType(cmd.investor_type),
            full_name=cmd.full_name,
            email=cmd.email,
            mobile=cmd.mobile,
            pan=pan,
            proposed_investment=Money.from_rupees(cmd.proposed_investment_inr),
            min_investment=Money(self._settings.min_investment_inr * 100),
        )

        self._repo.add(application)
        self._publisher.publish(application.pull_events())
        return to_view(application)
