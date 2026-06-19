"""Use-case tests for ConfirmEsignUseCase."""
from __future__ import annotations

import uuid
import pytest

from app.application.onboarding.ports import EsignPort, EsignResult
from app.application.onboarding.use_cases.confirm_esign import ConfirmEsignUseCase
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import InvestorType, KycSource, OnboardingStatus, RiskCategory
from app.domain.onboarding.value_objects import PAN, Aadhaar, BankAccount, DematAccount, Money
from tests.test_create_application import InMemoryOnboardingRepository, FakeEventPublisher


class AlwaysSignedEsign(EsignPort):
    def initiate(self, *, application_id, document_bytes):
        return "TX-1"
    def fetch_result(self, *, transaction_id):
        return EsignResult(signed=True, reference=transaction_id)


class NotYetSignedEsign(EsignPort):
    def initiate(self, *, application_id, document_bytes):
        return "TX-2"
    def fetch_result(self, *, transaction_id):
        return EsignResult(signed=False, reference=transaction_id)


def _app_at_agreement_pending() -> OnboardingApplication:
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
    app.pull_events()  # clear
    return app


def test_esign_happy_path():
    repo = InMemoryOnboardingRepository()
    app = _app_at_agreement_pending()
    repo.add(app)
    uc = ConfirmEsignUseCase(repo, AlwaysSignedEsign(), FakeEventPublisher())
    view = uc.execute(app.id, "TX-1")
    assert view.status == "under_review"


def test_esign_not_yet_signed():
    repo = InMemoryOnboardingRepository()
    app = _app_at_agreement_pending()
    repo.add(app)
    uc = ConfirmEsignUseCase(repo, NotYetSignedEsign(), FakeEventPublisher())
    with pytest.raises(ValidationError, match="not yet completed"):
        uc.execute(app.id, "TX-2")


def test_esign_not_found():
    repo = InMemoryOnboardingRepository()
    uc = ConfirmEsignUseCase(repo, AlwaysSignedEsign(), FakeEventPublisher())
    with pytest.raises(NotFoundError):
        uc.execute(uuid.uuid4(), "TX-1")
