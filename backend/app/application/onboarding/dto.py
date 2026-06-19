"""Application-layer DTOs (commands & read models).

These are plain dataclasses that cross the boundary between the API layer and the
use cases. They are intentionally separate from the API's Pydantic schemas and
from domain entities, so each layer can evolve independently.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateApplicationCommand:
    investor_type: str
    full_name: str
    email: str
    mobile: str
    pan: str
    proposed_investment_inr: float


@dataclass(frozen=True)
class SubmitKycCommand:
    application_id: uuid.UUID
    aadhaar_full: str
    bank_account_number: str
    bank_ifsc: str
    bank_holder_name: str
    demat_bo_id: str
    demat_depository: str


@dataclass(frozen=True)
class RiskAnswerInput:
    question_id: str
    weight: int


@dataclass(frozen=True)
class CompleteRiskProfileCommand:
    application_id: uuid.UUID
    answers: list[RiskAnswerInput]


@dataclass(frozen=True)
class ApproveCommand:
    application_id: uuid.UUID
    approved_by: str
    approve: bool
    reason: str | None = None


@dataclass(frozen=True)
class ApplicationView:
    """Read model returned to the API layer."""

    id: uuid.UUID
    status: str
    investor_type: str
    full_name: str
    email: str
    pan: str
    proposed_investment_inr: float
    risk_category: str | None
    kyc_source: str | None
