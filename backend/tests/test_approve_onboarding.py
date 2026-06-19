"""Use-case tests for ApproveOnboardingUseCase."""
from __future__ import annotations

import uuid
import pytest

from app.application.onboarding.dto import ApproveCommand
from app.application.onboarding.use_cases.approve_onboarding import ApproveOnboardingUseCase
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import InvestorType, KycSource, RiskCategory
from app.domain.onboarding.value_objects import PAN, Aadhaar, BankAccount, DematAccount, Money
from tests.test_create_application import InMemoryOnboardingRepository, FakeEventPublisher


def _app_under_review() -> OnboardingApplication:
    app = OnboardingApplication.create(
        investor_type=InvestorType.INDIVIDUAL, full_name="Asha Rao",
        email="asha@example.com", mobile="9876543210", pan=PAN("ABCDE1234F"),
        proposed_investment=Money.from_rupees(5_000_000), min_investment=Money(5_000_000 * 100),
    )
    app.submit_for_kyc(
        aadhaar=Aadhaar.from_full("234567890123"),
        bank_account=BankAccount("12345678901", "HDFC0001234", "Asha Rao"),
        demat_account=DematAccount("1234567812345678", "NSDL"),
    )
    app.mark_kyc_verified(source=KycSource.KRA, reference="KRA-1")
    app.set_risk_profile(category=RiskCategory.MODERATE, score=18)
    app.generate_agreement()
    app.mark_agreement_signed(esign_reference="ESIGN-1")
    app.pull_events()
    return app


def test_approve_success():
    repo = InMemoryOnboardingRepository()
    app = _app_under_review()
    repo.add(app)
    uc = ApproveOnboardingUseCase(repo, FakeEventPublisher())
    view = uc.execute(ApproveCommand(
        application_id=app.id, approved_by="compliance.officer", approve=True,
    ))
    assert view.status == "active"


def test_reject_success():
    repo = InMemoryOnboardingRepository()
    app = _app_under_review()
    repo.add(app)
    uc = ApproveOnboardingUseCase(repo, FakeEventPublisher())
    view = uc.execute(ApproveCommand(
        application_id=app.id, approved_by="compliance.officer",
        approve=False, reason="Incomplete documentation",
    ))
    assert view.status == "rejected"


def test_reject_without_reason_fails():
    repo = InMemoryOnboardingRepository()
    app = _app_under_review()
    repo.add(app)
    uc = ApproveOnboardingUseCase(repo, FakeEventPublisher())
    with pytest.raises(ValidationError, match="Rejection reason"):
        uc.execute(ApproveCommand(
            application_id=app.id, approved_by="co", approve=False, reason=None,
        ))


def test_approve_not_found():
    repo = InMemoryOnboardingRepository()
    uc = ApproveOnboardingUseCase(repo, FakeEventPublisher())
    with pytest.raises(NotFoundError):
        uc.execute(ApproveCommand(
            application_id=uuid.uuid4(), approved_by="co", approve=True,
        ))
