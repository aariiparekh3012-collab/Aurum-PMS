"""Pydantic request/response schemas for the v1 onboarding API.

These are the wire contract with the React client. They map to/from application
DTOs in the routers — never expose ORM models or domain entities directly.
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class CreateApplicationRequest(BaseModel):
    investor_type: str = Field(examples=["individual"])
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    mobile: str = Field(pattern=r"^[6-9]\d{9}$", examples=["9876543210"])
    pan: str = Field(examples=["ABCDE1234F"])
    proposed_investment_inr: float = Field(gt=0, examples=[5000000])


class SubmitKycRequest(BaseModel):
    aadhaar_full: str = Field(examples=["234567890123"])
    bank_account_number: str
    bank_ifsc: str = Field(examples=["HDFC0001234"])
    bank_holder_name: str
    demat_bo_id: str = Field(examples=["1234567812345678"])
    demat_depository: str = Field(examples=["NSDL"])


class RiskAnswerSchema(BaseModel):
    question_id: str
    weight: int = Field(ge=1, le=5)


class RiskProfileRequest(BaseModel):
    answers: list[RiskAnswerSchema] = Field(min_length=5)


class EsignConfirmRequest(BaseModel):
    transaction_id: str


class ApproveRequest(BaseModel):
    approve: bool
    reason: str | None = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    status: str
    investor_type: str
    full_name: str
    email: str
    pan: str
    proposed_investment_inr: float
    risk_category: str | None = None
    kyc_source: str | None = None
