"""Client Master application DTOs (read models)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BankAccountView:
    ifsc: str
    holder_name: str
    masked_account: str
    is_primary: bool


@dataclass(frozen=True)
class NomineeView:
    name: str
    share_percent: float
    rank: int
    relationship: str | None


@dataclass(frozen=True)
class ClientView:
    id: uuid.UUID
    client_code: str
    status: str
    investor_type: str
    full_name: str
    email: str
    mobile: str
    pan: str
    onboarding_application_id: uuid.UUID
    risk_category: str | None
    demat_bo_ids: list[str] = field(default_factory=list)
    bank_accounts: list[BankAccountView] = field(default_factory=list)
    nominees: list[NomineeView] = field(default_factory=list)
