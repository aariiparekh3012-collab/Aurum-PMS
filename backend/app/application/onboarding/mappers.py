"""Mapping helpers between domain entities and application read models (DTOs)."""
from __future__ import annotations

from app.application.onboarding.dto import ApplicationView
from app.domain.onboarding.entities import OnboardingApplication


def to_view(app: OnboardingApplication) -> ApplicationView:
    return ApplicationView(
        id=app.id,
        status=app.status.value,
        investor_type=app.investor_type.value,
        full_name=app.full_name,
        email=app.email,
        pan=app.pan.value,
        proposed_investment_inr=app.proposed_investment.rupees,
        risk_category=app.risk_category.value if app.risk_category else None,
        kyc_source=app.kyc_source.value if app.kyc_source else None,
    )
