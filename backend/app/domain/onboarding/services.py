"""Pure domain services — logic that doesn't naturally live on a single entity.

`RiskProfilingService` scores a SEBI-style suitability questionnaire and maps the
client to a risk category. Keeping it framework-free makes it trivially testable.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import ValidationError
from app.domain.onboarding.enums import RiskCategory


@dataclass(frozen=True)
class RiskAnswer:
    question_id: str
    weight: int  # normalised 1..5 (1 = most conservative, 5 = most aggressive)


class RiskProfilingService:
    """Scores the risk questionnaire and derives a suitability category.

    Score = sum(weights). Bands are deliberately simple and auditable; in
    production the bands/weights are config-driven and version-stamped so that
    each client's profile records *which* ruleset version scored them.
    """

    MIN_QUESTIONS = 5

    def score(self, answers: list[RiskAnswer]) -> tuple[RiskCategory, int]:
        if len(answers) < self.MIN_QUESTIONS:
            raise ValidationError(
                f"At least {self.MIN_QUESTIONS} risk questions required",
                code="insufficient_risk_answers",
            )
        if any(not 1 <= a.weight <= 5 for a in answers):
            raise ValidationError("Risk weights must be in 1..5", code="invalid_risk_weight")

        total = sum(a.weight for a in answers)
        max_possible = len(answers) * 5
        pct = total / max_possible

        if pct <= 0.40:
            category = RiskCategory.CONSERVATIVE
        elif pct <= 0.70:
            category = RiskCategory.MODERATE
        else:
            category = RiskCategory.AGGRESSIVE
        return category, total
