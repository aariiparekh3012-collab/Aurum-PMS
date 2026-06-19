"""Aggregate root: OnboardingApplication.

This is pure domain logic — no framework, no ORM, no I/O. It owns the lifecycle
state machine and guarantees that the business invariants of SEBI PMS onboarding
hold regardless of which use case drives it.
"""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field

from app.core.exceptions import InvalidStateTransition, ValidationError
from app.domain.onboarding import events
from app.domain.onboarding.enums import (
    InvestorType,
    KycSource,
    OnboardingStatus,
    RiskCategory,
)
from app.domain.onboarding.value_objects import (
    PAN,
    Aadhaar,
    BankAccount,
    DematAccount,
    Money,
)

# Allowed transitions for the onboarding state machine.
_TRANSITIONS: dict[OnboardingStatus, set[OnboardingStatus]] = {
    OnboardingStatus.DRAFT: {OnboardingStatus.KYC_PENDING},
    OnboardingStatus.KYC_PENDING: {
        OnboardingStatus.KYC_VERIFIED,
        OnboardingStatus.KYC_REJECTED,
    },
    OnboardingStatus.KYC_REJECTED: {OnboardingStatus.KYC_PENDING},
    OnboardingStatus.KYC_VERIFIED: {OnboardingStatus.RISK_PROFILED},
    OnboardingStatus.RISK_PROFILED: {OnboardingStatus.AGREEMENT_PENDING},
    OnboardingStatus.AGREEMENT_PENDING: {OnboardingStatus.AGREEMENT_SIGNED},
    OnboardingStatus.AGREEMENT_SIGNED: {OnboardingStatus.UNDER_REVIEW},
    OnboardingStatus.UNDER_REVIEW: {OnboardingStatus.ACTIVE, OnboardingStatus.REJECTED},
}


@dataclass
class OnboardingApplication:
    """Aggregate root for a single client's onboarding journey."""

    investor_type: InvestorType
    full_name: str
    email: str
    mobile: str
    pan: PAN
    proposed_investment: Money

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: OnboardingStatus = OnboardingStatus.DRAFT

    aadhaar: Aadhaar | None = None
    bank_account: BankAccount | None = None
    demat_account: DematAccount | None = None

    kyc_source: KycSource | None = None
    kyc_reference: str | None = None
    risk_category: RiskCategory | None = None
    risk_score: int | None = None
    agreement_esign_ref: str | None = None
    rejection_reason: str | None = None

    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    _events: list[events.DomainEvent] = field(default_factory=list, repr=False, init=False)

    # ---- event plumbing ----
    def pull_events(self) -> list[events.DomainEvent]:
        out, self._events = self._events, []
        return out

    def _transition(self, target: OnboardingStatus) -> None:
        allowed = _TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidStateTransition(
                f"Cannot move from {self.status.value} to {target.value}"
            )
        self.status = target
        self.updated_at = dt.datetime.now(dt.timezone.utc)

    # ---- lifecycle behaviours ----
    @classmethod
    def create(
        cls,
        *,
        investor_type: InvestorType,
        full_name: str,
        email: str,
        mobile: str,
        pan: PAN,
        proposed_investment: Money,
        min_investment: Money,
    ) -> "OnboardingApplication":
        if proposed_investment.paise < min_investment.paise:
            raise ValidationError(
                f"Proposed investment below SEBI minimum of "
                f"Rs {min_investment.rupees:,.0f}",
                code="below_min_investment",
            )
        app = cls(
            investor_type=investor_type,
            full_name=full_name.strip(),
            email=email.lower().strip(),
            mobile=mobile.strip(),
            pan=pan,
            proposed_investment=proposed_investment,
        )
        app._events.append(events.OnboardingApplicationCreated(aggregate_id=app.id))
        return app

    def submit_for_kyc(
        self,
        *,
        aadhaar: Aadhaar,
        bank_account: BankAccount,
        demat_account: DematAccount,
    ) -> None:
        self.aadhaar = aadhaar
        self.bank_account = bank_account
        self.demat_account = demat_account
        self._transition(OnboardingStatus.KYC_PENDING)

    def mark_kyc_verified(self, *, source: KycSource, reference: str) -> None:
        self.kyc_source = source
        self.kyc_reference = reference
        self._transition(OnboardingStatus.KYC_VERIFIED)
        self._events.append(events.KycVerified(aggregate_id=self.id, source=source.value))

    def mark_kyc_rejected(self, *, reason: str) -> None:
        self.rejection_reason = reason
        self._transition(OnboardingStatus.KYC_REJECTED)
        self._events.append(events.KycRejected(aggregate_id=self.id, reason=reason))

    def set_risk_profile(self, *, category: RiskCategory, score: int) -> None:
        self.risk_category = category
        self.risk_score = score
        self._transition(OnboardingStatus.RISK_PROFILED)
        self._events.append(
            events.RiskProfileCompleted(
                aggregate_id=self.id, category=category.value, score=score
            )
        )

    def generate_agreement(self) -> None:
        self._transition(OnboardingStatus.AGREEMENT_PENDING)

    def mark_agreement_signed(self, *, esign_reference: str) -> None:
        self.agreement_esign_ref = esign_reference
        self._transition(OnboardingStatus.AGREEMENT_SIGNED)
        self._events.append(
            events.AgreementSigned(aggregate_id=self.id, esign_reference=esign_reference)
        )
        # auto-advance to compliance review
        self._transition(OnboardingStatus.UNDER_REVIEW)

    def approve(self, *, approved_by: str) -> None:
        self._transition(OnboardingStatus.ACTIVE)
        self._events.append(
            events.OnboardingActivated(aggregate_id=self.id, approved_by=approved_by)
        )

    def reject(self, *, reason: str) -> None:
        self.rejection_reason = reason
        self._transition(OnboardingStatus.REJECTED)
