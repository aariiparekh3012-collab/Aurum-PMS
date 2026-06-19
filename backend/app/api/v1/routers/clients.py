"""Client Master REST endpoints (thin controllers)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api import dependencies as deps
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/clients", tags=["clients"])


# ---- response schemas ----
class BankAccountOut(BaseModel):
    ifsc: str
    holder_name: str
    masked_account: str
    is_primary: bool


class NomineeOut(BaseModel):
    name: str
    share_percent: float
    rank: int
    relationship: str | None = None


class ClientOut(BaseModel):
    id: uuid.UUID
    client_code: str
    status: str
    investor_type: str
    full_name: str
    email: str
    mobile: str
    pan: str
    onboarding_application_id: uuid.UUID
    risk_category: str | None = None
    demat_bo_ids: list[str] = []
    bank_accounts: list[BankAccountOut] = []
    nominees: list[NomineeOut] = []


class ProcessOutboxOut(BaseModel):
    processed: int


def _to_out(view) -> ClientOut:
    return ClientOut(
        **{**view.__dict__,
           "bank_accounts": [b.__dict__ for b in view.bank_accounts],
           "nominees": [n.__dict__ for n in view.nominees]}
    )


@router.get("", response_model=list[ClientOut])
def list_clients(
    limit: int = 50,
    offset: int = 0,
    repo=Depends(deps.get_client_repo),
    _user: dict = Depends(deps.require_staff),
):
    from app.application.client.mappers import to_view

    return [_to_out(to_view(c)) for c in repo.list(limit=limit, offset=offset)]


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: uuid.UUID,
    repo=Depends(deps.get_client_repo),
    _user: dict = Depends(deps.require_staff),
):
    from app.application.client.mappers import to_view

    client = repo.get(client_id)
    if client is None:
        raise NotFoundError("Client not found")
    return _to_out(to_view(client))


@router.post("/process-outbox", response_model=ProcessOutboxOut)
def process_outbox(
    dispatcher=Depends(deps.get_outbox_dispatcher),
    _user: dict = Depends(deps.require_compliance),
):
    """Dev/ops trigger: provision clients for any pending OnboardingActivated events."""
    return ProcessOutboxOut(processed=dispatcher.process_pending())
