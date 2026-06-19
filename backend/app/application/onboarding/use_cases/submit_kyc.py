"""Use case: submit KYC details — triggers penny-drop + KRA/CKYC verification."""
from __future__ import annotations

import uuid

from app.application.onboarding.dto import ApplicationView, SubmitKycCommand
from app.application.onboarding.mappers import to_view
from app.application.onboarding.ports import (
    BankVerificationPort, EventPublisher, KycPort,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.onboarding.enums import KycSource
from app.domain.onboarding.repositories import OnboardingRepository
from app.domain.onboarding.value_objects import Aadhaar, BankAccount, DematAccount


class SubmitKycUseCase:
    def __init__(
        self,
        repo: OnboardingRepository,
        kyc: KycPort,
        bank: BankVerificationPort,
        publisher: EventPublisher,
    ) -> None:
        self._repo = repo
        self._kyc = kyc
        self._bank = bank
        self._publisher = publisher

    def execute(self, cmd: SubmitKycCommand) -> ApplicationView:
        app = self._repo.get(cmd.application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")

        aadhaar = Aadhaar.from_full(cmd.aadhaar_full)
        bank = BankAccount(cmd.bank_account_number, cmd.bank_ifsc, cmd.bank_holder_name)
        demat = DematAccount(cmd.demat_bo_id, cmd.demat_depository)

        # Transition to KYC_PENDING (captures PII on the aggregate)
        app.submit_for_kyc(aadhaar=aadhaar, bank_account=bank, demat_account=demat)

        # Penny-drop bank verification
        bank_result = self._bank.verify(
            account_number=cmd.bank_account_number,
            ifsc=cmd.bank_ifsc,
            name=cmd.bank_holder_name,
        )
        if not bank_result.verified:
            app.mark_kyc_rejected(reason=f"Bank verification failed: {bank_result.reason}")
            self._repo.update(app)
            self._publisher.publish(app.pull_events())
            return to_view(app)

        # KRA/CKYC identity verification
        kyc_result = self._kyc.verify(
            pan=app.pan.value,
            aadhaar_last4=aadhaar.last4,
            name=app.full_name,
        )
        if kyc_result.verified:
            app.mark_kyc_verified(
                source=KycSource(kyc_result.source), reference=kyc_result.reference,
            )
        else:
            app.mark_kyc_rejected(reason=kyc_result.reason or "KYC verification failed")

        self._repo.update(app)
        self._publisher.publish(app.pull_events())
        return to_view(app)
