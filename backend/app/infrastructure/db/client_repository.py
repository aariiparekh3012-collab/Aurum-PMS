"""SQLAlchemy adapter implementing the ClientRepository port.

Data-Mapper translation between ORM rows and the Client aggregate, including PII
encryption/decryption and PAN hashing (same scheme as onboarding).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_pii, encrypt_pii
from app.domain.client.entities import (
    Client,
    ClientBankAccount,
    ClientDematAccount,
    ClientRiskProfile,
    Nominee,
)
from app.domain.client.enums import ClientStatus
from app.domain.client.repositories import ClientRepository
from app.domain.onboarding.enums import InvestorType, RiskCategory
from app.domain.onboarding.value_objects import PAN
from app.infrastructure.db.models_client import (
    ClientBankAccountModel,
    ClientDematAccountModel,
    ClientModel,
    ClientRiskProfileModel,
    NomineeModel,
)


def _pan_hash(pan: str) -> str:
    return hashlib.sha256(pan.upper().encode()).hexdigest()


class SqlAlchemyClientRepository(ClientRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    # ---- mapping ----
    def _to_model(self, e: Client) -> ClientModel:
        now = dt.datetime.now(dt.timezone.utc)
        return ClientModel(
            id=e.id,
            onboarding_application_id=e.onboarding_application_id,
            client_code=e.client_code,
            pan_hash=_pan_hash(e.pan.value),
            pan_enc=encrypt_pii(e.pan.value),
            status=e.status.value,
            investor_type=e.investor_type.value,
            full_name=e.full_name,
            email=e.email,
            mobile=e.mobile,
            created_at=e.created_at,
            updated_at=e.updated_at,
            bank_accounts=[
                ClientBankAccountModel(
                    id=b.id,
                    account_enc=encrypt_pii(b.account_number),
                    ifsc=b.ifsc,
                    holder_name=b.holder_name,
                    is_primary=b.is_primary,
                    created_at=now,
                )
                for b in e.bank_accounts
            ],
            demat_accounts=[
                ClientDematAccountModel(
                    id=d.id, bo_id=d.bo_id, depository=d.depository, created_at=now
                )
                for d in e.demat_accounts
            ],
            nominees=[
                NomineeModel(
                    id=n.id,
                    name_enc=encrypt_pii(n.name),
                    relationship_=n.relationship,
                    share_percent=n.share_percent,
                    rank=n.rank,
                    created_at=now,
                )
                for n in e.nominees
            ],
            risk_profiles=[
                ClientRiskProfileModel(
                    id=r.id,
                    score=r.score,
                    category=r.category.value,
                    ruleset_version=r.ruleset_version,
                    effective_from=r.effective_from,
                    created_at=now,
                )
                for r in e.risk_profiles
            ],
        )

    def _to_entity(self, m: ClientModel) -> Client:
        return Client(
            id=m.id,
            onboarding_application_id=m.onboarding_application_id,
            client_code=m.client_code,
            pan=PAN(decrypt_pii(m.pan_enc)),
            investor_type=InvestorType(m.investor_type),
            full_name=m.full_name,
            email=m.email,
            mobile=m.mobile,
            status=ClientStatus(m.status),
            created_at=m.created_at,
            updated_at=m.updated_at,
            bank_accounts=[
                ClientBankAccount(
                    id=b.id,
                    account_number=decrypt_pii(b.account_enc),
                    ifsc=b.ifsc,
                    holder_name=b.holder_name,
                    is_primary=b.is_primary,
                )
                for b in m.bank_accounts
            ],
            demat_accounts=[
                ClientDematAccount(id=d.id, bo_id=d.bo_id, depository=d.depository)
                for d in m.demat_accounts
            ],
            nominees=[
                Nominee(
                    id=n.id,
                    name=decrypt_pii(n.name_enc),
                    relationship=n.relationship_,
                    share_percent=float(n.share_percent),
                    rank=n.rank,
                )
                for n in m.nominees
            ],
            risk_profiles=[
                ClientRiskProfile(
                    id=r.id,
                    score=r.score,
                    category=RiskCategory(r.category),
                    ruleset_version=r.ruleset_version,
                    effective_from=r.effective_from,
                )
                for r in m.risk_profiles
            ],
        )

    # ---- port ----
    def add(self, client: Client) -> None:
        self._s.add(self._to_model(client))
        self._s.flush()

    def get(self, client_id: uuid.UUID) -> Client | None:
        m = self._s.get(ClientModel, client_id)
        return self._to_entity(m) if m else None

    def get_by_pan(self, pan: str) -> Client | None:
        stmt = select(ClientModel).where(ClientModel.pan_hash == _pan_hash(pan))
        m = self._s.scalars(stmt).first()
        return self._to_entity(m) if m else None

    def get_by_onboarding_application_id(self, application_id: uuid.UUID) -> Client | None:
        stmt = select(ClientModel).where(
            ClientModel.onboarding_application_id == application_id
        )
        m = self._s.scalars(stmt).first()
        return self._to_entity(m) if m else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[Client]:
        stmt = (
            select(ClientModel)
            .order_by(ClientModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(m) for m in self._s.scalars(stmt).all()]
