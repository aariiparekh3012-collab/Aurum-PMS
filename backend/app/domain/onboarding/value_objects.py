"""Immutable value objects with built-in validation.

Value objects encapsulate format rules (PAN, Aadhaar, IFSC ...) so invalid data
can never exist inside the domain. They are frozen dataclasses — equality by value.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.exceptions import ValidationError

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_AADHAAR_RE = re.compile(r"^[2-9][0-9]{11}$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_DEMAT_RE = re.compile(r"^[0-9]{16}$")  # NSDL/CDSL 16-digit DP+client id


@dataclass(frozen=True, slots=True)
class PAN:
    value: str

    def __post_init__(self) -> None:
        if not _PAN_RE.match(self.value):
            raise ValidationError(f"Invalid PAN format: {self.value}", code="invalid_pan")

    @property
    def fourth_char(self) -> str:
        """4th char encodes holder type (P=individual, C=company, H=HUF...)."""
        return self.value[3]


@dataclass(frozen=True, slots=True)
class Aadhaar:
    """Stores ONLY the last 4 digits in the clear; full value is encrypted at rest.

    SEBI/UIDAI mandate masking of Aadhaar — never persist the full number unmasked.
    """

    last4: str

    def __post_init__(self) -> None:
        if not (self.last4.isdigit() and len(self.last4) == 4):
            raise ValidationError("Aadhaar last4 must be 4 digits", code="invalid_aadhaar")

    @classmethod
    def from_full(cls, full: str) -> "Aadhaar":
        if not _AADHAAR_RE.match(full):
            raise ValidationError("Invalid Aadhaar number", code="invalid_aadhaar")
        return cls(last4=full[-4:])

    @property
    def masked(self) -> str:
        return f"XXXX-XXXX-{self.last4}"


@dataclass(frozen=True, slots=True)
class BankAccount:
    account_number: str
    ifsc: str
    holder_name: str

    def __post_init__(self) -> None:
        if not _IFSC_RE.match(self.ifsc):
            raise ValidationError(f"Invalid IFSC: {self.ifsc}", code="invalid_ifsc")
        if not (8 <= len(self.account_number) <= 18 and self.account_number.isdigit()):
            raise ValidationError("Invalid bank account number", code="invalid_bank_account")


@dataclass(frozen=True, slots=True)
class DematAccount:
    bo_id: str        # 16-digit beneficiary owner id
    depository: str   # NSDL | CDSL

    def __post_init__(self) -> None:
        if not _DEMAT_RE.match(self.bo_id):
            raise ValidationError("Invalid demat BO id", code="invalid_demat")
        if self.depository not in ("NSDL", "CDSL"):
            raise ValidationError("Depository must be NSDL or CDSL", code="invalid_depository")


@dataclass(frozen=True, slots=True)
class Money:
    """Integer paise to avoid floating-point errors in financial amounts."""

    paise: int

    def __post_init__(self) -> None:
        if self.paise < 0:
            raise ValidationError("Money cannot be negative", code="invalid_money")

    @classmethod
    def from_rupees(cls, rupees: float) -> "Money":
        return cls(paise=round(rupees * 100))

    @property
    def rupees(self) -> float:
        return self.paise / 100
