"""Investor-facing portal endpoints.

Scoped to the logged-in investor's own data. The JWT `sub` claim is matched
against client.email to find their client record.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import decrypt_pii
from app.infrastructure.db.models_client import ClientModel
from app.infrastructure.db.models_portfolio import (
    CashLedgerModel,
    HoldingModel,
    PortfolioAccountModel,
)
from app.infrastructure.db.models_reference import SecurityModel, StrategyModel
from app.infrastructure.db.models_onboarding import OnboardingApplicationModel

router = APIRouter(prefix="/investor", tags=["investor portal"])


# ── Schemas ────────────────────────────────────────────────────────────────

class InvestorProfile(BaseModel):
    client_id: uuid.UUID
    full_name: str
    client_code: str
    pan: str
    email: str
    status: str
    risk_category: str | None = None
    investor_type: str

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    account_id: uuid.UUID
    account_code: str
    strategy_name: str
    status: str
    inception_date: date
    holdings_count: int
    total_cost_paise: int


class HoldingDetail(BaseModel):
    security_symbol: str
    security_isin: str
    sector: str | None = None
    quantity: float
    avg_cost_paise: int
    cost_value_paise: int


class CashEntry(BaseModel):
    entry_type: str
    amount_paise: int
    balance_paise: int
    posted_on: date

    class Config:
        from_attributes = True


class OnboardingStatus(BaseModel):
    id: uuid.UUID
    status: str
    full_name: str
    pan: str
    proposed_investment_inr: float
    kyc_source: str | None = None
    risk_category: str | None = None

    class Config:
        from_attributes = True


class InvestorDashboard(BaseModel):
    profile: InvestorProfile | None = None
    onboarding: OnboardingStatus | None = None
    portfolios: list[PortfolioSummary] = []
    total_invested_paise: int = 0


# ── Helpers ────────────────────────────────────────────────────────────────

def _require_investor(user: dict = Depends(deps.get_current_user)) -> dict:
    if user.get("role") != "investor":
        raise HTTPException(status_code=403, detail="Investor role required")
    return user


def _find_client(db: Session, subject: str) -> ClientModel | None:
    """Match the JWT subject to a client record by email (case-insensitive)."""
    return db.scalar(
        select(ClientModel).where(ClientModel.email == subject.lower())
    )


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=InvestorDashboard)
def investor_dashboard(
    db: Session = Depends(get_db),
    user: dict = Depends(_require_investor),
):
    """Main investor portal — profile + portfolio summaries."""
    subject = user.get("sub", "")
    client = _find_client(db, subject)

    # If not yet a client, check onboarding status
    if not client:
        app = db.scalar(
            select(OnboardingApplicationModel)
            .where(OnboardingApplicationModel.email == subject.lower())
            .order_by(OnboardingApplicationModel.created_at.desc())
        )
        onboarding = None
        if app:
            onboarding = OnboardingStatus(
                id=app.id,
                status=app.status,
                full_name=app.full_name,
                pan=decrypt_pii(app.pan_enc),
                proposed_investment_inr=float(app.proposed_investment_paise) / 100,
                kyc_source=app.kyc_source,
                risk_category=app.risk_category,
            )
        return InvestorDashboard(onboarding=onboarding)

    # Build profile — derive risk_category from latest risk profile row
    latest_risk = (
        max(client.risk_profiles, key=lambda r: r.effective_from)
        if client.risk_profiles
        else None
    )
    profile = InvestorProfile(
        client_id=client.id,
        full_name=client.full_name,
        client_code=client.client_code,
        pan=decrypt_pii(client.pan_enc),
        email=client.email,
        status=client.status,
        risk_category=latest_risk.category if latest_risk else None,
        investor_type=client.investor_type,
    )

    # Portfolio accounts
    accounts = db.scalars(
        select(PortfolioAccountModel).where(PortfolioAccountModel.client_id == client.id)
    ).all()

    portfolios: list[PortfolioSummary] = []
    total_invested = 0
    for acct in accounts:
        holdings = db.scalars(
            select(HoldingModel).where(HoldingModel.portfolio_account_id == acct.id)
        ).all()
        cost = sum(int(h.avg_cost_paise * float(h.quantity)) for h in holdings)
        total_invested += cost

        strat = db.get(StrategyModel, acct.strategy_id)
        portfolios.append(PortfolioSummary(
            account_id=acct.id,
            account_code=acct.account_code,
            strategy_name=strat.name if strat else "Unknown",
            status=acct.status,
            inception_date=acct.inception_date,
            holdings_count=len(holdings),
            total_cost_paise=cost,
        ))

    return InvestorDashboard(
        profile=profile,
        portfolios=portfolios,
        total_invested_paise=total_invested,
    )


@router.get("/holdings/{account_id}", response_model=list[HoldingDetail])
def investor_holdings(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(_require_investor),
):
    """Holdings for one of the investor's portfolio accounts."""
    subject = user.get("sub", "")
    client = _find_client(db, subject)
    if not client:
        raise NotFoundError("Client record not found")

    # Verify account belongs to this investor
    acct = db.get(PortfolioAccountModel, account_id)
    if not acct or acct.client_id != client.id:
        raise AuthorizationError("Portfolio account not found or access denied")

    holdings = db.scalars(
        select(HoldingModel).where(HoldingModel.portfolio_account_id == account_id)
    ).all()

    result = []
    for h in holdings:
        sec = db.get(SecurityModel, h.security_id)
        result.append(HoldingDetail(
            security_symbol=sec.symbol if sec else "???",
            security_isin=sec.isin if sec else "???",
            sector=sec.sector if sec else None,
            quantity=float(h.quantity),
            avg_cost_paise=int(h.avg_cost_paise),
            cost_value_paise=int(h.avg_cost_paise * float(h.quantity)),
        ))
    return result


@router.get("/cash/{account_id}", response_model=list[CashEntry])
def investor_cash(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(_require_investor),
):
    """Cash ledger for one of the investor's portfolio accounts."""
    subject = user.get("sub", "")
    client = _find_client(db, subject)
    if not client:
        raise NotFoundError("Client record not found")

    acct = db.get(PortfolioAccountModel, account_id)
    if not acct or acct.client_id != client.id:
        raise AuthorizationError("Portfolio account not found or access denied")

    entries = db.scalars(
        select(CashLedgerModel)
        .where(CashLedgerModel.portfolio_account_id == account_id)
        .order_by(CashLedgerModel.posted_on.desc())
        .limit(100)
    ).all()
    return entries
