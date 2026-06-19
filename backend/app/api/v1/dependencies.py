"""Composition root — wires concrete adapters to application ports.

This is the ONLY place in the codebase where concrete infrastructure classes
are imported. Swapping a vendor or using fakes is a one-line change here.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token

# ── Ports / adapters ─────────────────────────────────────────────────────
from app.infrastructure.audit.audit_logger import AuditLogger
from app.infrastructure.audit.event_publisher import OutboxEventPublisher
from app.infrastructure.db.repository import SqlAlchemyOnboardingRepository
from app.infrastructure.external.bank_verification_client import (
    FakeBankVerificationAdapter,
    PennyDropAdapter,
    SurepassPennyDropAdapter,
)
from app.infrastructure.external.esign_client import (
    AadhaarEsignAdapter,
    DigioEsignAdapter,
    FakeEsignAdapter,
)
from app.infrastructure.external.kyc_client import FakeKycAdapter, KraKycAdapter, SurepassKycAdapter

# ── Use cases ────────────────────────────────────────────────────────────
from app.application.onboarding.use_cases.approve_onboarding import ApproveOnboardingUseCase
from app.application.onboarding.use_cases.complete_risk_profile import CompleteRiskProfileUseCase
from app.application.onboarding.use_cases.confirm_esign import ConfirmEsignUseCase
from app.application.onboarding.use_cases.create_application import CreateApplicationUseCase
from app.application.onboarding.use_cases.get_application import GetApplicationUseCase
from app.application.onboarding.use_cases.submit_kyc import SubmitKycUseCase
from app.domain.onboarding.services import RiskProfilingService

_bearer = HTTPBearer(auto_error=False)


# ── Auth dependencies ────────────────────────────────────────────────────

def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing auth token")
    try:
        return decode_access_token(creds.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def require_role(*roles: str):
    """Factory that returns a dependency enforcing one of the given roles."""
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user
    return _check


# ── Use-case factories ──────────────────────────────────────────────────

def _get_kyc_adapter():
    """Return Surepass if credentials present, else fake."""
    s = get_settings()
    if s.surepass_api_token:
        return SurepassKycAdapter()
    return FakeKycAdapter()


def _get_bank_adapter():
    """Return Surepass penny-drop if credentials present, else fake."""
    s = get_settings()
    if s.surepass_api_token:
        return SurepassPennyDropAdapter()
    return FakeBankVerificationAdapter()


def _get_esign_adapter():
    """Return Digio if credentials present, else fake."""
    s = get_settings()
    if s.digio_client_id and s.digio_client_secret:
        return DigioEsignAdapter()
    return FakeEsignAdapter()


def get_create_application_uc(db: Session = Depends(get_db)) -> CreateApplicationUseCase:
    return CreateApplicationUseCase(
        repo=SqlAlchemyOnboardingRepository(db),
        publisher=OutboxEventPublisher(db),
    )


def get_submit_kyc_uc(db: Session = Depends(get_db)) -> SubmitKycUseCase:
    return SubmitKycUseCase(
        repo=SqlAlchemyOnboardingRepository(db),
        kyc=_get_kyc_adapter(),
        bank=_get_bank_adapter(),
        publisher=OutboxEventPublisher(db),
    )


def get_risk_profile_uc(db: Session = Depends(get_db)) -> CompleteRiskProfileUseCase:
    return CompleteRiskProfileUseCase(
        repo=SqlAlchemyOnboardingRepository(db),
        scorer=RiskProfilingService(),
        publisher=OutboxEventPublisher(db),
    )


def get_confirm_esign_uc(db: Session = Depends(get_db)) -> ConfirmEsignUseCase:
    return ConfirmEsignUseCase(
        repo=SqlAlchemyOnboardingRepository(db),
        esign=_get_esign_adapter(),
        publisher=OutboxEventPublisher(db),
    )


def get_approve_uc(db: Session = Depends(get_db)) -> ApproveOnboardingUseCase:
    return ApproveOnboardingUseCase(
        repo=SqlAlchemyOnboardingRepository(db),
        publisher=OutboxEventPublisher(db),
    )


def get_query_uc(db: Session = Depends(get_db)) -> GetApplicationUseCase:
    return GetApplicationUseCase(repo=SqlAlchemyOnboardingRepository(db))
