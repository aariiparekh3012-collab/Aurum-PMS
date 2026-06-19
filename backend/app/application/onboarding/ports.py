"""Application PORTS for regulated external integrations.

The use cases depend on these abstractions, not on concrete HTTP clients. Adapters
live in infrastructure/external. This is what makes the integrations mockable in
tests and swappable between vendors (e.g. CVL KRA vs NDML KRA).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class KycResult:
    verified: bool
    source: str          # kra | ckyc | manual
    reference: str       # KRA/CKYC record id
    reason: str | None = None


@dataclass(frozen=True)
class BankVerificationResult:
    verified: bool
    name_match_score: float  # 0..1 from penny-drop name match
    reason: str | None = None


@dataclass(frozen=True)
class EsignResult:
    signed: bool
    reference: str           # eSign transaction / document id
    signed_document_url: str | None = None


class KycPort(ABC):
    """Verifies identity via a KYC Registration Agency or Central KYC registry."""

    @abstractmethod
    def verify(self, *, pan: str, aadhaar_last4: str, name: str) -> KycResult: ...


class BankVerificationPort(ABC):
    """Penny-drop / reverse-penny-drop bank account validation."""

    @abstractmethod
    def verify(self, *, account_number: str, ifsc: str, name: str) -> BankVerificationResult: ...


class EsignPort(ABC):
    """Aadhaar eSign (NSDL/UIDAI ASP) for the PMS agreement."""

    @abstractmethod
    def initiate(self, *, application_id: str, document_bytes: bytes) -> str:
        """Returns an eSign session/transaction id."""

    @abstractmethod
    def fetch_result(self, *, transaction_id: str) -> EsignResult: ...


class EventPublisher(ABC):
    """Publishes domain events to the outbox / message bus."""

    @abstractmethod
    def publish(self, events: list) -> None: ...
