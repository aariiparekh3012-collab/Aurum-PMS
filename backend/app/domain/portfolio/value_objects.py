"""Portfolio value objects."""
from __future__ import annotations
from dataclasses import dataclass
from app.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class ISIN:
    """12-character International Securities Identification Number."""
    value: str
    def __post_init__(self):
        if not (len(self.value) == 12 and self.value[:2].isalpha() and self.value[2:].isalnum()):
            raise ValidationError(f"Invalid ISIN: {self.value}", code="invalid_isin")


@dataclass(frozen=True, slots=True)
class Quantity:
    """Non-negative quantity (supports fractional for MF units)."""
    value: float
    def __post_init__(self):
        if self.value < 0:
            raise ValidationError("Quantity cannot be negative", code="invalid_quantity")


@dataclass(frozen=True, slots=True)
class Price:
    """Price in paise (integer) to avoid floating-point errors."""
    paise: int
    def __post_init__(self):
        if self.paise < 0:
            raise ValidationError("Price cannot be negative", code="invalid_price")

    @classmethod
    def from_rupees(cls, rupees: float) -> "Price":
        return cls(paise=round(rupees * 100))

    @property
    def rupees(self) -> float:
        return self.paise / 100


@dataclass(frozen=True, slots=True)
class Weight:
    """Strategy weight as a percentage (0-100)."""
    pct: float
    def __post_init__(self):
        if not 0 <= self.pct <= 100:
            raise ValidationError("Weight must be 0-100%", code="invalid_weight")
