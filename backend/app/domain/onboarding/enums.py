"""Onboarding domain enumerations.

These model the regulatory lifecycle of a PMS client application. The
`OnboardingStatus` state machine is the heart of the bounded context.
"""
from __future__ import annotations

from enum import Enum


class OnboardingStatus(str, Enum):
    """Finite-state lifecycle of a client onboarding application.

    Allowed transitions are enforced in `entities.OnboardingApplication`.
    """

    DRAFT = "draft"                          # application created, details being captured
    KYC_PENDING = "kyc_pending"              # PII captured, awaiting KRA/CKYC verification
    KYC_VERIFIED = "kyc_verified"            # KYC confirmed by KRA/CKYC
    KYC_REJECTED = "kyc_rejected"            # KYC failed / mismatch
    RISK_PROFILED = "risk_profiled"          # risk questionnaire scored
    AGREEMENT_PENDING = "agreement_pending"  # PMS agreement generated, awaiting e-sign
    AGREEMENT_SIGNED = "agreement_signed"    # Aadhaar eSign / wet-sign completed
    UNDER_REVIEW = "under_review"            # compliance maker-checker review
    ACTIVE = "active"                        # onboarded; ready to accept funds
    REJECTED = "rejected"                    # rejected by compliance


class InvestorType(str, Enum):
    INDIVIDUAL = "individual"
    HUF = "huf"
    NRI = "nri"
    CORPORATE = "corporate"
    PARTNERSHIP = "partnership"
    TRUST = "trust"


class KycSource(str, Enum):
    KRA = "kra"        # KYC Registration Agency (CVL, NDML, CAMS, Karvy, NSE)
    CKYC = "ckyc"      # Central KYC Records Registry (CERSAI)
    MANUAL = "manual"  # in-person / officer-verified fallback


class RiskCategory(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class DocumentType(str, Enum):
    PAN = "pan"
    AADHAAR = "aadhaar"
    PASSPORT = "passport"
    BANK_PROOF = "bank_proof"
    DEMAT_CMR = "demat_cmr"          # Client Master Report
    PHOTO = "photo"
    PMS_AGREEMENT = "pms_agreement"
    FATCA_CRS = "fatca_crs"
