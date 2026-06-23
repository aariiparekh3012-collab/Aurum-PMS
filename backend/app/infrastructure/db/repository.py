"""SQLAlchemy implementation of OnboardingRepository (Data Mapper pattern)."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.security import decrypt, encrypt, hash_pan
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import (
    InvestorType, KycSource, OnboardingStatus, RiskCategory,
)
from app.domain.onboarding.repositories import OnboardingRepository
from app.domain.onboarding.value_objects import (
    PAN, Aadhaar, BankAccount, DematAccount, Money,
)
from app.infrastructure.db.models_onboarding import OnboardingApplicationModel


class SqlAlchemyOnboardingRepository(OnboardingRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    # ── mapping helpers ──────────────────────────────────────────────────

    def _to_model(self, app: OnboardingApplication) -> OnboardingApplicationModel:
        return OnboardingApplicationModel(
            id=app.id,
            status=app.status.value,
            investor_type=app.investor_type.value,
            full_name=app.full_name,
            email=app.email,
            mobile=app.mobile,
            pan_hash=hash_pan(app.pan.value),
            pan_enc=encrypt(app.pan.value),
            aadhaar_last4=app.aadhaar.last4 if app.aadhaar else None,
            aadhaar_enc=encrypt(app.aadhaar.last4) if app.aadhaar else None,
            bank_account_enc=encrypt(app.bank_account.account_number) if app.bank_account else None,
            bank_ifsc=app.bank_account.ifsc if app.bank_account else None,
            bank_holder_name=app.bank_account.holder_name if app.bank_account else None,
            demat_bo_id=app.demat_account.bo_id if app.demat_account else None,
            demat_depository=app.demat_account.depository if app.demat_account else None,
            proposed_investment_paise=app.proposed_investment.paise,
            kyc_source=app.kyc_source.value if app.kyc_source else None,
            kyc_reference=app.kyc_reference,
            risk_category=app.risk_category.value if app.risk_category else None,
            risk_score=app.risk_score,
            agreement_esign_ref=app.agreement_esign_ref,
            rejection_reason=app.rejection_reason,
            created_at=app.created_at,
            updated_at=app.updated_at,
        )

    def _to_entity(self, m: OnboardingApplicationModel) -> OnboardingApplication:
        pan_plain = decrypt(m.pan_enc)
        bank = None
        if m.bank_account_enc:
            bank = BankAccount(
                account_number=decrypt(m.bank_account_enc),
                ifsc=m.bank_ifsc,
                holder_name=m.bank_holder_name,
            )
        demat = None
        if m.demat_bo_id:
            demat = DematAccount(bo_id=m.demat_bo_id, depository=m.demat_depository)
        aadhaar = Aadhaar(last4=m.aadhaar_last4) if m.aadhaar_last4 else None

        return OnboardingApplication(
            id=m.id,
            status=OnboardingStatus(m.status),
            investor_type=InvestorType(m.investor_type),
            full_name=m.full_name,
            email=m.email,
            mobile=m.mobile,
            pan=PAN(pan_plain),
            proposed_investment=Money(paise=m.proposed_investment_paise),
            aadhaar=aadhaar,
            bank_account=bank,
            demat_account=demat,
            kyc_source=KycSource(m.kyc_source) if m.kyc_source else None,
            kyc_reference=m.kyc_reference,
            risk_category=RiskCategory(m.risk_category) if m.risk_category else None,
            risk_score=m.risk_score,
            agreement_esign_ref=m.agreement_esign_ref,
            rejection_reason=m.rejection_reason,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    # ── repository interface ─────────────────────────────────────────────

    def add(self, application: OnboardingApplication) -> None:
        self._s.add(self._to_model(application))
        self._s.flush()

    def get(self, application_id: uuid.UUID) -> OnboardingApplication | None:
        m = self._s.get(OnboardingApplicationModel, application_id)
        return self._to_entity(m) if m else None

    def get_by_pan(self, pan: str) -> OnboardingApplication | None:
        h = hash_pan(pan)
        m = (
            self._s.query(OnboardingApplicationModel)
            .filter(OnboardingApplicationModel.pan_hash == h)
            .first()
        )
        return self._to_entity(m) if m else None

    def update(self, application: OnboardingApplication) -> None:
        m = self._s.get(OnboardingApplicationModel, application.id)
        if m is None:
            raise ValueError(f"Application {application.id} not found for update")
        m.status = application.status.value
        m.aadhaar_last4 = application.aadhaar.last4 if application.aadhaar else None
        m.aadhaar_enc = encrypt(application.aadhaar.last4) if application.aadhaar else None
        m.bank_account_enc = encrypt(application.bank_account.account_number) if application.bank_account else None
        m.bank_ifsc = application.bank_account.ifsc if application.bank_account else None
        m.bank_holder_name = application.bank_account.holder_name if application.bank_account else None
        m.demat_bo_id = application.demat_account.bo_id if application.demat_account else None
        m.demat_depository = application.demat_account.depository if application.demat_account else None
        m.kyc_source = application.kyc_source.value if application.kyc_source else None
        m.kyc_reference = application.kyc_reference
        m.risk_category = application.risk_category.value if application.risk_category else None
        m.risk_score = application.risk_score
        m.agreement_esign_ref = application.agreement_esign_ref
        m.rejection_reason = application.rejection_reason
        m.updated_at = application.updated_at
        self._s.flush()

    def list(self, *, offset: int = 0, limit: int = 50) -> list[OnboardingApplication]:
        rows = (
            self._s.query(OnboardingApplicationModel)
            .order_by(OnboardingApplicationModel.created_at.desc())
            .offset(offset).limit(limit).all()
        )
        return [self._to_entity(r) for r in rows]

    def list_by_status(
        self, status: OnboardingStatus, *, offset: int = 0, limit: int = 50,
    ) -> list[OnboardingApplication]:
        rows = (
            self._s.query(OnboardingApplicationModel)
            .filter(OnboardingApplicationModel.status == status.value)
            .order_by(OnboardingApplicationModel.created_at.desc())
            .offset(offset).limit(limit).all()
        )
        return [self._to_entity(r) for r in rows]

    def count_by_status(self, status: OnboardingStatus) -> int:
        return (
            self._s.query(OnboardingApplicationModel)
            .filter(OnboardingApplicationModel.status == status.value)
            .count()
        )
