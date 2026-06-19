"""Onboarding API endpoints — the full lifecycle from DRAFT to ACTIVE."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import (
    get_confirm_esign_uc,
    get_create_application_uc,
    get_approve_uc,
    get_current_user,
    get_query_uc,
    get_risk_profile_uc,
    get_submit_kyc_uc,
    require_role,
)
from app.api.v1.schemas import (
    ApplicationResponse,
    ApproveRequest,
    CreateApplicationRequest,
    EsignConfirmRequest,
    RiskProfileRequest,
    SubmitKycRequest,
)
from app.application.onboarding.dto import (
    ApproveCommand,
    CompleteRiskProfileCommand,
    CreateApplicationCommand,
    RiskAnswerInput,
    SubmitKycCommand,
)
from app.application.onboarding.use_cases.approve_onboarding import ApproveOnboardingUseCase
from app.application.onboarding.use_cases.complete_risk_profile import CompleteRiskProfileUseCase
from app.application.onboarding.use_cases.confirm_esign import ConfirmEsignUseCase
from app.application.onboarding.use_cases.create_application import CreateApplicationUseCase
from app.application.onboarding.use_cases.get_application import GetApplicationUseCase
from app.application.onboarding.use_cases.submit_kyc import SubmitKycUseCase

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/applications", response_model=ApplicationResponse, status_code=201)
def create_application(
    body: CreateApplicationRequest,
    uc: CreateApplicationUseCase = Depends(get_create_application_uc),
    _user: dict = Depends(get_current_user),
):
    cmd = CreateApplicationCommand(
        investor_type=body.investor_type,
        full_name=body.full_name,
        email=body.email,
        mobile=body.mobile,
        pan=body.pan,
        proposed_investment_inr=body.proposed_investment_inr,
    )
    view = uc.execute(cmd)
    return ApplicationResponse(**view.__dict__)


@router.get("/applications/{app_id}", response_model=ApplicationResponse)
def get_application(
    app_id: uuid.UUID,
    uc: GetApplicationUseCase = Depends(get_query_uc),
    _user: dict = Depends(get_current_user),
):
    view = uc.get(app_id)
    return ApplicationResponse(**view.__dict__)


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    status: str = Query("under_review"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    uc: GetApplicationUseCase = Depends(get_query_uc),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    views = uc.list_by_status(status, offset=offset, limit=limit)
    return [ApplicationResponse(**v.__dict__) for v in views]


@router.post("/applications/{app_id}/kyc", response_model=ApplicationResponse)
def submit_kyc(
    app_id: uuid.UUID,
    body: SubmitKycRequest,
    uc: SubmitKycUseCase = Depends(get_submit_kyc_uc),
    _user: dict = Depends(get_current_user),
):
    cmd = SubmitKycCommand(
        application_id=app_id,
        aadhaar_full=body.aadhaar_full,
        bank_account_number=body.bank_account_number,
        bank_ifsc=body.bank_ifsc,
        bank_holder_name=body.bank_holder_name,
        demat_bo_id=body.demat_bo_id,
        demat_depository=body.demat_depository,
    )
    view = uc.execute(cmd)
    return ApplicationResponse(**view.__dict__)


@router.post("/applications/{app_id}/risk-profile", response_model=ApplicationResponse)
def complete_risk_profile(
    app_id: uuid.UUID,
    body: RiskProfileRequest,
    uc: CompleteRiskProfileUseCase = Depends(get_risk_profile_uc),
    _user: dict = Depends(get_current_user),
):
    cmd = CompleteRiskProfileCommand(
        application_id=app_id,
        answers=[RiskAnswerInput(question_id=a.question_id, weight=a.weight) for a in body.answers],
    )
    view = uc.execute(cmd)
    return ApplicationResponse(**view.__dict__)


@router.post("/applications/{app_id}/esign/confirm", response_model=ApplicationResponse)
def confirm_esign(
    app_id: uuid.UUID,
    body: EsignConfirmRequest,
    uc: ConfirmEsignUseCase = Depends(get_confirm_esign_uc),
    _user: dict = Depends(get_current_user),
):
    view = uc.execute(app_id, body.transaction_id)
    return ApplicationResponse(**view.__dict__)


@router.post("/applications/{app_id}/decision", response_model=ApplicationResponse)
def approve_or_reject(
    app_id: uuid.UUID,
    body: ApproveRequest,
    uc: ApproveOnboardingUseCase = Depends(get_approve_uc),
    user: dict = Depends(require_role("compliance")),
):
    cmd = ApproveCommand(
        application_id=app_id,
        approved_by=user["sub"],
        approve=body.approve,
        reason=body.reason,
    )
    view = uc.execute(cmd)
    return ApplicationResponse(**view.__dict__)
