"""Unit tests for the pure RiskProfilingService domain logic."""
from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.domain.onboarding.enums import RiskCategory
from app.domain.onboarding.services import RiskAnswer, RiskProfilingService


def _answers(weights: list[int]) -> list[RiskAnswer]:
    return [RiskAnswer(question_id=f"q{i}", weight=w) for i, w in enumerate(weights)]


def test_conservative_band():
    cat, score = RiskProfilingService().score(_answers([1, 1, 1, 2, 1]))
    assert cat is RiskCategory.CONSERVATIVE
    assert score == 6


def test_aggressive_band():
    cat, _ = RiskProfilingService().score(_answers([5, 5, 4, 5, 4]))
    assert cat is RiskCategory.AGGRESSIVE


def test_too_few_answers_rejected():
    with pytest.raises(ValidationError):
        RiskProfilingService().score(_answers([3, 3]))


def test_out_of_range_weight_rejected():
    with pytest.raises(ValidationError):
        RiskProfilingService().score(_answers([3, 3, 3, 3, 9]))
