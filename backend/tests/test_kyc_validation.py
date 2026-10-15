"""Validation of the current onboarding/KYC wire contract and domain values."""
from __future__ import annotations

import pytest
from pydantic import ValidationError as SchemaError

from app.api.v1.schemas import CreateApplicationRequest, SubmitKycRequest
from app.core.exceptions import ValidationError
from app.domain.onboarding.value_objects import PAN, Aadhaar, BankAccount, DematAccount

_APPLICATION = {
    "investor_type": "individual",
    "full_name": "Asha Rao",
    "email": "asha@example.com",
    "mobile": "9876543210",
    "pan": "AAAPA1234A",
    "proposed_investment_inr": 5_000_000,
}

_KYC = {
    "aadhaar_full": "234567890123",
    "bank_account_number": "123456789012",
    "bank_ifsc": "HDFC0001234",
    "bank_holder_name": "Asha Rao",
    "demat_bo_id": "1234567812345678",
    "demat_depository": "NSDL",
}


@pytest.mark.parametrize("pan", ["AAAPA1234A", "BBBPB5678B"])
def test_valid_pan(pan):
    assert PAN(pan).value == pan


@pytest.mark.parametrize("pan", ["ABC", "", "AAAPA1234AA", "AAAPA12341", "AAA-PL-5055K"])
def test_invalid_pan(pan):
    with pytest.raises(ValidationError) as exc:
        PAN(pan)
    assert exc.value.code == "invalid_pan"


def test_application_mobile_and_investment():
    assert CreateApplicationRequest(**_APPLICATION).mobile == "9876543210"


@pytest.mark.parametrize("mobile", ["1234", "98765abcde", "+919876543210", "1234567890"])
def test_invalid_mobile(mobile):
    with pytest.raises(SchemaError):
        CreateApplicationRequest(**{**_APPLICATION, "mobile": mobile})


@pytest.mark.parametrize("amount", [0, -1])
def test_nonpositive_investment(amount):
    with pytest.raises(SchemaError):
        CreateApplicationRequest(**{**_APPLICATION, "proposed_investment_inr": amount})


def test_invalid_email_and_name():
    for change in ({"email": "invalid"}, {"full_name": ""}):
        with pytest.raises(SchemaError):
            CreateApplicationRequest(**{**_APPLICATION, **change})


def test_kyc_schema_and_masked_aadhaar():
    assert SubmitKycRequest(**_KYC).bank_ifsc == "HDFC0001234"
    aadhaar = Aadhaar.from_full(_KYC["aadhaar_full"])
    assert aadhaar.last4 == "0123"
    assert aadhaar.masked == "XXXX-XXXX-0123"


@pytest.mark.parametrize("number", ["1234", "123456789012", "23456789012A"])
def test_invalid_aadhaar(number):
    with pytest.raises(ValidationError) as exc:
        Aadhaar.from_full(number)
    assert exc.value.code == "invalid_aadhaar"


@pytest.mark.parametrize("change", [
    {"ifsc": "INVALID"}, {"account_number": "123"},
])
def test_invalid_bank_details(change):
    with pytest.raises(ValidationError):
        BankAccount(**{
            "account_number": "123456789012", "ifsc": "HDFC0001234",
            "holder_name": "Asha Rao", **change,
        })


@pytest.mark.parametrize("bo_id,depository", [
    ("123", "NSDL"), ("1234567812345678", "OTHER"),
])
def test_invalid_demat_details(bo_id, depository):
    with pytest.raises(ValidationError):
        DematAccount(bo_id=bo_id, depository=depository)
