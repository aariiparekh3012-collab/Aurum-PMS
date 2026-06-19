"""Unit tests for the OnboardingApplication aggregate state machine."""
from __future__ import annotations

import pytest

from app.core.exceptions import InvalidStateTransition, ValidationError
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import InvestorType, KycSource, OnboardingStatus, RiskCategory
from app.domain.onboarding.value_objects import (
    PAN,
    Aadhaar,
    BankAccount,
    DematAccount,
    Money,
)

MIN = Money(5_000_000 * 100)


def _new_app(investment_inr: float = 5_000_000) -> OnboardingApplication:
    return OnboardingApplication.create(
        investor_type=InvestorType.INDIVIDUAL,
        full_name="Asha Rao",
        email="asha@example.com",
        mobile="9876543210",
        pan=PAN("ABCDE1234F"),
        proposed_investment=Money.from_rupees(investment_inr),
        min_investment=MIN,
    )


def test_create_below_minimum_rejected():
    with pytest.raises(ValidationError):
        _new_app(investment_inr=1_000_000)


def test_happy_path_to_active():
    app = _new_app()
    assert app.status is OnboardingStatus.DRAFT
    app.submit_for_kyc(
        aadhaar=Aadhaar.from_full("234567890123"),
        bank_account=BankAccount("12345678901", "HDFC0001234", "Asha Rao"),
        demat_account=DematAccount("1234567812345678", "NSDL"),
    )
    app.mark_kyc_verified(source=KycSource.KRA, reference="KRA-1")
    app.set_risk_profile(category=RiskCategory.MODERATE, score=18)
    app.generate_agreement()
    app.mark_agreement_signed(esign_reference="ESIGN-1")
    assert app.status is OnboardingStatus.UNDER_REVIEW
    app.approve(approved_by="compliance.officer")
    assert app.status is OnboardingStatus.ACTIVE


def test_illegal_transition_blocked():
    app = _new_app()
    with pytest.raises(InvalidStateTransition):
        app.approve(approved_by="x")  # cannot approve from DRAFT
