"""Read-only endpoints over onboarding applications (compliance work-queue).

Kept separate from onboarding.py so the onboarding write flow stays untouched.
These power the frontend Applications / compliance panel.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api import dependencies as deps
from app.api.v1.schemas import ApplicationResponse
from app.application.onboarding.mappers import to_view
from app.domain.onboarding.enums import OnboardingStatus

router = APIRouter(prefix="/onboarding/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    repo=Depends(deps.get_repo),
    _user: dict = Depends(deps.get_current_user),
):
    if status:
        try:
            apps = repo.list_by_status(OnboardingStatus(status), limit=limit, offset=offset)
        except ValueError:
            apps = []
    else:
        apps = repo.list(limit=limit, offset=offset)
    return [ApplicationResponse(**to_view(a).__dict__) for a in apps]
