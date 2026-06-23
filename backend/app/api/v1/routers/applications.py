"""Read-only endpoints over onboarding applications (compliance work-queue).

Kept separate from onboarding.py so the onboarding write flow stays untouched.
These power the frontend Applications / compliance panel.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api import dependencies as deps
from app.api.v1.schemas import ApplicationResponse
from app.application.onboarding.mappers import to_view
from app.domain.onboarding.enums import OnboardingStatus

router = APIRouter(prefix="/onboarding/applications", tags=["applications"])


@router.get("")
def list_applications(
    status: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    repo=Depends(deps.get_repo),
    _user: dict = Depends(deps.require_staff),
):
    if status:
        try:
            apps = repo.list_by_status(OnboardingStatus(status), limit=limit, offset=offset)
        except ValueError:
            apps = []
    else:
        apps = repo.list(limit=limit, offset=offset)
    items = [ApplicationResponse(**to_view(a).__dict__) for a in apps]
    return {"applications": items, "total": len(items), "limit": limit, "offset": offset}
