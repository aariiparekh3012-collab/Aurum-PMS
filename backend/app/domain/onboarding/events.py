"""Domain events.

Emitted by aggregates on meaningful state changes. The application layer collects
and dispatches them (e.g. to an outbox table / message bus) for downstream modules
— audit trail, notifications, portfolio provisioning — keeping the domain decoupled.
"""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainEvent:
    aggregate_id: uuid.UUID
    occurred_at: dt.datetime = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )


@dataclass(frozen=True)
class OnboardingApplicationCreated(DomainEvent):
    pass


@dataclass(frozen=True)
class KycVerified(DomainEvent):
    source: str = ""  # kra | ckyc | manual


@dataclass(frozen=True)
class KycRejected(DomainEvent):
    reason: str = ""


@dataclass(frozen=True)
class RiskProfileCompleted(DomainEvent):
    category: str = ""
    score: int = 0


@dataclass(frozen=True)
class AgreementSigned(DomainEvent):
    esign_reference: str = ""


@dataclass(frozen=True)
class OnboardingActivated(DomainEvent):
    """Signals downstream portfolio module to provision the client account."""

    approved_by: str = ""
