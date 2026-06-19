"""FastAPI dependency wiring (the Composition Root).

This is the ONLY place where concrete adapters are bound to ports. Swapping a KYC
vendor or using fakes in tests is a one-line change here. Auth/role guards live
here too.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.onboarding.use_cases.approve_onboarding import ApproveOnboardingUseCase
from app.application.onboarding.use_cases.complete_risk_profile import (
    CompleteRiskProfileUseCase,
)
from app.application.onboarding.use_cases.create_application import CreateApplicationUseCase
from app.application.onboarding.use_cases.esign_agreement import EsignAgreementUseCase
from app.application.onboarding.use_cases.submit_kyc import SubmitKycUseCase
from app.application.client.use_cases.provision_client import ProvisionClientUseCase
from app.application.portfolio.use_cases.provision_client import (
    ProvisionClientUseCase as PortfolioProvisionClientUseCase,
)
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import DomainError
from app.core.security import decode_access_token
from app.domain.onboarding.services import RiskProfilingService
from app.infrastructure.audit.event_publisher import OutboxEventPublisher
from app.infrastructure.db.repositories import SqlAlchemyOnboardingRepository
from app.infrastructure.db.client_repository import SqlAlchemyClientRepository
from app.infrastructure.db.portfolio_repository import (
    SqlAlchemyClientRepository as SqlAlchemyPortfolioClientRepository,
)
from app.infrastructure.events.outbox_dispatcher import OutboxDispatcher
from app.infrastructure.external.redis_message_bus import RedisMessageBus
from app.infrastructure.external.bank_verification_client import (
    FakeBankVerificationAdapter,
    SurepassPennyDropAdapter,
)
from app.infrastructure.external.esign_client import (
    DigioEsignAdapter,
    FakeEsignAdapter,
)
from app.infrastructure.external.kra_client import FakeKycAdapter, SurepassKycAdapter


# ---- auth ----
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return decode_access_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def require_compliance(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "compliance":
        raise HTTPException(status_code=403, detail="Compliance role required")
    return user


def require_staff(user: dict = Depends(get_current_user)) -> dict:
    """Allow internal staff (compliance or relationship manager); block investors."""
    if user.get("role") not in ("compliance", "relationship_manager"):
        raise HTTPException(status_code=403, detail="Staff role required")
    return user


def current_client_id(db: Session, user: dict):
    """Resolve the caller's data scope.

    Returns None for staff (compliance/RM) → full access. For an investor,
    returns their own ClientModel.id (matched by JWT subject/email) so callers
    can restrict rows to that client. Any other role is denied.
    """
    role = user.get("role")
    if role in ("compliance", "relationship_manager"):
        return None
    if role == "investor":
        from sqlalchemy import select
        from app.infrastructure.db.models_client import ClientModel

        client = db.scalar(
            select(ClientModel).where(ClientModel.email == user.get("sub", "").lower())
        )
        if client is None:
            raise HTTPException(status_code=403, detail="No client record for this investor")
        return client.id
    raise HTTPException(status_code=403, detail="Access denied")


# ---- repositories & adapters ----
def get_repo(db: Session = Depends(get_db)) -> SqlAlchemyOnboardingRepository:
    return SqlAlchemyOnboardingRepository(db)


def get_publisher(db: Session = Depends(get_db)) -> OutboxEventPublisher:
    return OutboxEventPublisher(db)


def get_kyc_adapter(settings: Settings = Depends(get_settings)):
    """Return Surepass adapter if credentials are configured, else fake."""
    if settings.surepass_api_token:
        return SurepassKycAdapter()
    return FakeKycAdapter()


def get_bank_adapter(settings: Settings = Depends(get_settings)):
    """Return Surepass penny-drop adapter if credentials are configured, else fake."""
    if settings.surepass_api_token:
        return SurepassPennyDropAdapter()
    return FakeBankVerificationAdapter()


def get_esign_adapter(settings: Settings = Depends(get_settings)):
    """Return Digio adapter if credentials are configured, else fake."""
    if settings.digio_client_id and settings.digio_client_secret:
        return DigioEsignAdapter()
    return FakeEsignAdapter()


# ---- use cases ----
def create_application_uc(
    repo=Depends(get_repo), pub=Depends(get_publisher)
) -> CreateApplicationUseCase:
    return CreateApplicationUseCase(repo, pub)


def submit_kyc_uc(
    repo=Depends(get_repo),
    kyc=Depends(get_kyc_adapter),
    bank=Depends(get_bank_adapter),
    pub=Depends(get_publisher),
) -> SubmitKycUseCase:
    return SubmitKycUseCase(repo, kyc, bank, pub)


def risk_profile_uc(
    repo=Depends(get_repo), pub=Depends(get_publisher)
) -> CompleteRiskProfileUseCase:
    return CompleteRiskProfileUseCase(repo, RiskProfilingService(), pub)


def esign_uc(
    repo=Depends(get_repo),
    esign=Depends(get_esign_adapter),
    pub=Depends(get_publisher),
) -> EsignAgreementUseCase:
    return EsignAgreementUseCase(repo, esign, pub)


def approve_uc(
    repo=Depends(get_repo), pub=Depends(get_publisher)
) -> ApproveOnboardingUseCase:
    return ApproveOnboardingUseCase(repo, pub)


# ---- Client Master ----
def get_client_repo(db: Session = Depends(get_db)) -> SqlAlchemyClientRepository:
    return SqlAlchemyClientRepository(db)


def provision_client_uc(
    onboarding_repo=Depends(get_repo),
    client_repo=Depends(get_client_repo),
) -> ProvisionClientUseCase:
    return ProvisionClientUseCase(onboarding_repo, client_repo)


def _get_message_bus():
    """Return RedisMessageBus if REDIS_URL is configured, else None (NoOp)."""
    s = get_settings()
    if s.redis_url:
        return RedisMessageBus()
    return None  # OutboxDispatcher defaults to NoOpMessageBus


def get_portfolio_client_repo(db: Session = Depends(get_db)) -> SqlAlchemyPortfolioClientRepository:
    return SqlAlchemyPortfolioClientRepository(db)


def provision_portfolio_client_uc(
    onboarding_repo=Depends(get_repo),
    portfolio_client_repo=Depends(get_portfolio_client_repo),
) -> PortfolioProvisionClientUseCase:
    return PortfolioProvisionClientUseCase(onboarding_repo, portfolio_client_repo)


def get_outbox_dispatcher(
    db: Session = Depends(get_db),
    provision=Depends(provision_client_uc),
    provision_portfolio=Depends(provision_portfolio_client_uc),
) -> OutboxDispatcher:
    return OutboxDispatcher(
        db, provision,
        provision_portfolio_client=provision_portfolio,
        message_bus=_get_message_bus(),
    )
