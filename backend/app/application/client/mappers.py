"""Mapping between Client domain entity and client read models."""
from __future__ import annotations

from app.application.client.dto import BankAccountView, ClientView, NomineeView
from app.domain.client.entities import Client


def _mask_account(acc: str) -> str:
    return f"XXXXXX{acc[-4:]}" if len(acc) >= 4 else "XXXX"


def to_view(c: Client) -> ClientView:
    latest_risk = c.risk_profiles[-1].category.value if c.risk_profiles else None
    return ClientView(
        id=c.id,
        client_code=c.client_code,
        status=c.status.value,
        investor_type=c.investor_type.value,
        full_name=c.full_name,
        email=c.email,
        mobile=c.mobile,
        pan=c.pan.value,
        onboarding_application_id=c.onboarding_application_id,
        risk_category=latest_risk,
        demat_bo_ids=[d.bo_id for d in c.demat_accounts],
        bank_accounts=[
            BankAccountView(
                ifsc=b.ifsc,
                holder_name=b.holder_name,
                masked_account=_mask_account(b.account_number),
                is_primary=b.is_primary,
            )
            for b in c.bank_accounts
        ],
        nominees=[
            NomineeView(
                name=n.name, share_percent=n.share_percent, rank=n.rank,
                relationship=n.relationship,
            )
            for n in c.nominees
        ],
    )
