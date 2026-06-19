"""Use case: list onboarding applications pending compliance review.

Returns applications in UNDER_REVIEW status with pagination. Only accessible to
users with the `compliance` role.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.onboarding.enums import OnboardingStatus
from app.domain.onboarding.repositories import OnboardingRepository


@dataclass(frozen=True)
class ListReviewApplicationsQuery:
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class ApplicationListView:
    """Summary view for listing applications for review."""

    id: str
    full_name: str
    email: str
    mobile: str
    investor_type: str
    proposed_investment_inr: float
    status: str
    created_at: str
    updated_at: str


class ListApplicationsForReviewUseCase:
    def __init__(self, repo: OnboardingRepository) -> None:
        self._repo = repo

    def execute(self, query: ListReviewApplicationsQuery) -> tuple[list[ApplicationListView], int]:
        """Return (applications, total_count) for paginated listing."""
        applications = self._repo.list_by_status(
            OnboardingStatus.UNDER_REVIEW, limit=query.limit, offset=query.offset
        )
        views = [
            ApplicationListView(
                id=str(app.id),
                full_name=app.full_name,
                email=app.email,
                mobile=app.mobile,
                investor_type=app.investor_type.value,
                proposed_investment_inr=app.proposed_investment.rupees,
                status=app.status.value,
                created_at=app.created_at.isoformat(),
                updated_at=app.updated_at.isoformat(),
            )
            for app in applications
        ]
        total = self._repo.count_by_status(OnboardingStatus.UNDER_REVIEW)
        return views, total
