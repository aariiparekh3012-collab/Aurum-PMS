"""Client Master aggregate.

The `Client` is the durable golden record provisioned when an onboarding application
reaches ACTIVE. It reuses the onboarding value objects (PAN, BankAccount, ...) as a
shared kernel, so identity/format rules are defined once across the platform.

Pure domain — no framework, no ORM.
"""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field

from app.domain.client.enums import ClientStatus
from app.domain.onboarding.enums import InvestorType, RiskCategory
from app.domain.onboarding.value_objects import PAN, BankAccount, DematAccount


@dataclass
class ClientBankAccount:
    account_number: str
    ifsc: str
    holder_name: str
    is_primary: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class ClientDematAccount:
    bo_id: str
    depository: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class Nominee:
    name: str
    share_percent: float
    rank: int
    relationship: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class ClientRiskProfile:
    score: int
    category: RiskCategory
    effective_from: dt.date
    ruleset_version: int = 1
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class Client:
    """Golden record for an onboarded investor."""

    onboarding_application_id: uuid.UUID
    client_code: str
    pan: PAN
    investor_type: InvestorType
    full_name: str
    email: str
    mobile: str

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: ClientStatus = ClientStatus.ACTIVE

    bank_accounts: list[ClientBankAccount] = field(default_factory=list)
    demat_accounts: list[ClientDematAccount] = field(default_factory=list)
    nominees: list[Nominee] = field(default_factory=list)
    risk_profiles: list[ClientRiskProfile] = field(default_factory=list)

    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    @classmethod
    def from_onboarding(
        cls,
        *,
        application_id: uuid.UUID,
        client_code: str,
        pan: PAN,
        investor_type: InvestorType,
        full_name: str,
        email: str,
        mobile: str,
        bank_account: BankAccount | None,
        demat_account: DematAccount | None,
        risk_category: RiskCategory | None,
        risk_score: int | None,
    ) -> "Client":
        client = cls(
            onboarding_application_id=application_id,
            client_code=client_code,
            pan=pan,
            investor_type=investor_type,
            full_name=full_name,
            email=email,
            mobile=mobile,
        )
        if bank_account is not None:
            client.bank_accounts.append(
                ClientBankAccount(
                    account_number=bank_account.account_number,
                    ifsc=bank_account.ifsc,
                    holder_name=bank_account.holder_name,
                    is_primary=True,
                )
            )
        if demat_account is not None:
            client.demat_accounts.append(
                ClientDematAccount(
                    bo_id=demat_account.bo_id, depository=demat_account.depository
                )
            )
        if risk_category is not None and risk_score is not None:
            client.risk_profiles.append(
                ClientRiskProfile(
                    score=risk_score,
                    category=risk_category,
                    effective_from=dt.date.today(),
                    ruleset_version=1,
                )
            )
        return client

    def add_nominee(self, *, name: str, share_percent: float, rank: int,
                    relationship: str | None = None) -> None:
        total = sum(n.share_percent for n in self.nominees) + share_percent
        if total > 100.0:
            raise ValueError("Total nominee share cannot exceed 100%")
        if any(n.rank == rank for n in self.nominees):
            raise ValueError(f"Nominee rank {rank} already used")
        self.nominees.append(
            Nominee(name=name, share_percent=share_percent, rank=rank,
                    relationship=relationship)
        )
