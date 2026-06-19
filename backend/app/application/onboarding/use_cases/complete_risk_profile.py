"""Use case: score the risk questionnaire and attach a suitability profile."""
from __future__ import annotations

from app.application.onboarding.dto import ApplicationView, CompleteRiskProfileCommand
from app.application.onboarding.mappers import to_view
from app.application.onboarding.ports import EventPublisher
from app.core.exceptions import NotFoundError
from app.domain.onboarding.repositories import OnboardingRepository
from app.domain.onboarding.services import RiskAnswer, RiskProfilingService


class CompleteRiskProfileUseCase:
    def __init__(
        self,
        repo: OnboardingRepository,
        scorer: RiskProfilingService,
        publisher: EventPublisher,
    ) -> None:
        self._repo = repo
        self._scorer = scorer
        self._publisher = publisher

    def execute(self, cmd: CompleteRiskProfileCommand) -> ApplicationView:
        app = self._repo.get(cmd.application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")

        answers = [RiskAnswer(question_id=a.question_id, weight=a.weight) for a in cmd.answers]
        category, score = self._scorer.score(answers)

        app.set_risk_profile(category=category, score=score)
        # Once risk-profiled, immediately generate the PMS agreement draft.
        app.generate_agreement()

        self._repo.update(app)
        self._publisher.publish(app.pull_events())
        return to_view(app)
