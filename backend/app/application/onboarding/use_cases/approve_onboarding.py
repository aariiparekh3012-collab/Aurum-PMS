"""Use case: compliance maker-checker approval / rejection.

Emits `OnboardingActivated` which the portfolio module consumes to provision the
client's PMS account. Only users with the `compliance` role may call this (enforced
at the API dependency layer).
"""
from __future__ import annotations

from app.application.onboarding.dto import ApplicationView, ApproveCommand
from app.application.onboarding.mappers import to_view
from app.application.onboarding.ports import EventPublisher
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.onboarding.repositories import OnboardingRepository


class ApproveOnboardingUseCase:
    def __init__(self, repo: OnboardingRepository, publisher: EventPublisher) -> None:
        self._repo = repo
        self._publisher = publisher

    def execute(self, cmd: ApproveCommand) -> ApplicationView:
        app = self._repo.get(cmd.application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")

        if cmd.approve:
            app.approve(approved_by=cmd.approved_by)
        else:
            if not cmd.reason:
                raise ValidationError("Rejection reason is required", code="reason_required")
            app.reject(reason=cmd.reason)

        self._repo.update(app)
        self._publisher.publish(app.pull_events())
        return to_view(app)
