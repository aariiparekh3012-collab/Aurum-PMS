"""SQLAlchemy adapter implementing the domain repository PORT.

Handles the Data Mapper translation between ORM rows and rich domain entities,
including PII encryption/decryption and PAN hashing for unique lookups.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_pii, encrypt_pii, hash_pan
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import (
    InvestorType,
    KycSource,
    OnboardingStatus,
    RiskCategory,
)
from app.domain.onboarding.repositories import OnboardingRepository
from app.domain.onboarding.value_objects import (
    PAN,
    Aadhaar,
    BankAccount,
    DematAccount,
    Money,
)
from app.infrastructure.db.models import OnboardingApplicationModel


class SqlAlchemyOnboardingRepository(OnboardingRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    # ---- mapping ----
    def _to_model(self, e: OnboardingApplication) -> OnboardingApplicationModel:
        return OnboardingApplicationModel(
            id=e.id,
            status=e.status.value,
            investor_type=e.investor_type.value,
            full_name=e.full_name,
            email=e.email,
            mobile=e.mobile,
            pan_hash=hash_pan(e.pan.value),
            pan_enc=encrypt_pii(e.pan.value),
            aadhaar_last4=e.aadhaar.last4 if e.aadhaar else None,
            aadhaar_enc=encrypt_pii(e.aadhaar.last4) if e.aadhaar else None,
            bank_account_enc=(
                encrypt_pii(e.bank_account.account_number) if e.bank_account else None
            ),
            bank_ifsc=e.bank_account.ifsc if e.bank_account else None,
            bank_holder_name=e.bank_account.holder_name if e.bank_account else None,
            demat_bo_id=e.demat_account.bo_id if e.demat_account else None,
            demat_depository=e.demat_account.depository if e.demat_account else None,
            proposed_investment_paise=e.proposed_investment.paise,
            kyc_source=e.kyc_source.value if e.kyc_source else None,
            kyc_reference=e.kyc_reference,
            risk_category=e.risk_category.value if e.risk_category else None,
            risk_score=e.risk_score,
            agreement_esign_ref=e.agreement_esign_ref,
            rejection_reason=e.rejection_reason,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )

    def _to_entity(self, m: OnboardingApplicationModel) -> OnboardingApplication:
        e = OnboardingApplication(
            id=m.id,
            investor_type=InvestorType(m.investor_type),
            full_name=m.full_name,
            email=m.email,
            mobile=m.mobile,
            pan=PAN(decrypt_pii(m.pan_enc)),
            proposed_investment=Money(m.proposed_investment_paise),
            status=OnboardingStatus(m.status),
        )
        if m.aadhaar_last4:
            e.aadhaar = Aadhaar(last4=m.aadhaar_last4)
        if m.bank_account_enc and m.bank_ifsc:
            e.bank_account = BankAccount(
                account_number=decrypt_pii(m.bank_account_enc),
                ifsc=m.bank_ifsc,
                holder_name=m.bank_holder_name or "",
            )
        if m.demat_bo_id and m.demat_depository:
            e.demat_account = DematAccount(bo_id=m.demat_bo_id, depository=m.demat_depository)
        e.kyc_source = KycSource(m.kyc_source) if m.kyc_source else None
        e.kyc_reference = m.kyc_reference
        e.risk_category = RiskCategory(m.risk_category) if m.risk_category else None
        e.risk_score = m.risk_score
        e.agreement_esign_ref = m.agreement_esign_ref
        e.rejection_reason = m.rejection_reason
        e.created_at = m.created_at
        e.updated_at = m.updated_at
        return e

    # ---- port implementation ----
    def add(self, application: OnboardingApplication) -> None:
        self._s.add(self._to_model(application))
        self._s.flush()

    def get(self, application_id: uuid.UUID) -> OnboardingApplication | None:
        m = self._s.get(OnboardingApplicationModel, application_id)
        return self._to_entity(m) if m else None

    def get_by_pan(self, pan: str) -> OnboardingApplication | None:
        stmt = select(OnboardingApplicationModel).where(
            OnboardingApplicationModel.pan_hash == hash_pan(pan)
        )
        m = self._s.scalars(stmt).first()
        return self._to_entity(m) if m else None

    def update(self, application: OnboardingApplication) -> None:
        m = self._s.get(OnboardingApplicationModel, application.id)
        if m is None:
            raise ValueError("Application not found for update")
        fresh = self._to_model(application)
        for col in OnboardingApplicationModel.__table__.columns.keys():
            if col in ("id", "created_at"):
                continue
            setattr(m, col, getattr(fresh, col))
        m.updated_at = dt.datetime.now(dt.timezone.utc)
        self._s.flush()

    def list(self, *, limit: int = 50, offset: int = 0) -> list[OnboardingApplication]:
        stmt = (
            select(OnboardingApplicationModel)
            .order_by(OnboardingApplicationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in self._s.scalars(stmt).all()]

    def count_by_status(self, status: OnboardingStatus) -> int:
        from sqlalchemy import func as _func, select as _select
        stmt = _select(_func.count()).select_from(OnboardingApplicationModel).where(
            OnboardingApplicationModel.status == status.value
        )
        return int(self._s.scalar(stmt) or 0)

    def list_by_status(
        self, status: OnboardingStatus, *, limit: int = 50, offset: int = 0
    ) -> list[OnboardingApplication]:
        stmt = (
            select(OnboardingApplicationModel)
            .where(OnboardingApplicationModel.status == status.value)
            .order_by(OnboardingApplicationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in self._s.scalars(stmt).all()]
