"""Use-case tests for SubmitKycUseCase."""
from __future__ import annotations

import uuid
import pytest

from app.application.onboarding.dto import SubmitKycCommand
from app.application.onboarding.ports import BankVerificationPort, BankVerificationResult, KycPort, KycResult
from app.application.onboarding.use_cases.submit_kyc import SubmitKycUseCase
from app.core.exceptions import NotFoundError
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import InvestorType, OnboardingStatus
from app.domain.onboarding.value_objects import PAN, Money

# reuse the in-memory repo/publisher from test_create_application
from tests.test_create_application import InMemoryOnboardingRepository, FakeEventPublisher


class AlwaysPassKyc(KycPort):
    def verify(self, *, pan, aadhaar_last4, name):
        return KycResult(verified=True, source="kra", reference="KRA-TEST-1")


class AlwaysFailKyc(KycPort):
    def verify(self, *, pan, aadhaar_last4, name):
        return KycResult(verified=False, source="kra", reference="", reason="Name mismatch")


class AlwaysPassBank(BankVerificationPort):
    def verify(self, *, account_number, ifsc, name):
        return BankVerificationResult(verified=True, name_match_score=0.98)


class AlwaysFailBank(BankVerificationPort):
    def verify(self, *, account_number, ifsc, name):
        return BankVerificationResult(verified=False, name_match_score=0.1, reason="Account not found")


def _draft_app() -> OnboardingApplication:
    return OnboardingApplication.create(
        investor_type=InvestorType.INDIVIDUAL, full_name="Asha Rao",
        email="asha@example.com", mobile="9876543210", pan=PAN("ABCDE1234F"),
        proposed_investment=Money.from_rupees(5_000_000), min_investment=Money(5_000_000 * 100),
    )


def _kyc_cmd(app_id: uuid.UUID) -> SubmitKycCommand:
    return SubmitKycCommand(
        application_id=app_id, aadhaar_full="234567890123",
        bank_account_number="12345678901", bank_ifsc="HDFC0001234",
        bank_holder_name="Asha Rao", demat_bo_id="1234567812345678", demat_depository="NSDL",
    )


def test_kyc_happy_path():
    repo = InMemoryOnboardingRepository()
    app = _draft_app()
    repo.add(app)
    uc = SubmitKycUseCase(repo, AlwaysPassKyc(), AlwaysPassBank(), FakeEventPublisher())
    view = uc.execute(_kyc_cmd(app.id))
    assert view.status == "kyc_verified"


def test_kyc_bank_fail_rejects():
    repo = InMemoryOnboardingRepository()
    app = _draft_app()
    repo.add(app)
    uc = SubmitKycUseCase(repo, AlwaysPassKyc(), AlwaysFailBank(), FakeEventPublisher())
    view = uc.execute(_kyc_cmd(app.id))
    assert view.status == "kyc_rejected"


def test_kyc_identity_fail_rejects():
    repo = InMemoryOnboardingRepository()
    app = _draft_app()
    repo.add(app)
    uc = SubmitKycUseCase(repo, AlwaysFailKyc(), AlwaysPassBank(), FakeEventPublisher())
    view = uc.execute(_kyc_cmd(app.id))
    assert view.status == "kyc_rejected"


def test_kyc_not_found():
    repo = InMemoryOnboardingRepository()
    uc = SubmitKycUseCase(repo, AlwaysPassKyc(), AlwaysPassBank(), FakeEventPublisher())
    with pytest.raises(NotFoundError):
        uc.execute(_kyc_cmd(uuid.uuid4()))
