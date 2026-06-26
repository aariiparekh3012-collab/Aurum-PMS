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
from app.infrastructure.db.models_onboarding import (
    OnboardingApplicationModel,
    OnboardingDocumentModel,
)
from app.infrastructure.db.models_performance import (
    PerformanceReturnModel,
    ValuationSnapshotModel,
)
from app.infrastructure.db.models_market_data import SecurityPriceModel

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
    market_value_paise: int = 0
    cash_balance_paise: int = 0
    unrealised_pnl_paise: int = 0


class HoldingDetail(BaseModel):
    security_symbol: str
    security_isin: str
    sector: str | None = None
    quantity: float
    avg_cost_paise: int
    cost_value_paise: int
    market_price_paise: int = 0
    market_value_paise: int = 0
    unrealised_pnl_paise: int = 0
    day_change_pct: float = 0.0


class CashEntry(BaseModel):
    entry_type: str
    amount_paise: int
    balance_paise: int
    posted_on: date

    class Config:
        from_attributes = True


class PerformanceReturn(BaseModel):
    period: str
    twrr_pct: float
    mwrr_pct: float | None = None
    benchmark_pct: float | None = None
    as_of: date


class ValuationPoint(BaseModel):
    as_of: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int


class FeeEntry(BaseModel):
    entry_type: str
    amount_paise: int
    posted_on: date
    description: str = ""


class DocumentInfo(BaseModel):
    id: uuid.UUID
    document_type: str
    uploaded_at: str
    download_url: str | None = None


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
    total_market_value_paise: int = 0
    total_unrealised_pnl_paise: int = 0
    total_cash_paise: int = 0
    returns: list[PerformanceReturn] = []


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
    total_market = 0
    total_cash = 0

    for acct in accounts:
        holdings = db.scalars(
            select(HoldingModel).where(HoldingModel.portfolio_account_id == acct.id)
        ).all()
        cost = sum(int(h.avg_cost_paise * float(h.quantity)) for h in holdings)
        total_invested += cost

        # Latest valuation snapshot for market value
        latest_snap = db.scalar(
            select(ValuationSnapshotModel)
            .where(ValuationSnapshotModel.portfolio_account_id == acct.id)
            .order_by(ValuationSnapshotModel.as_of.desc())
            .limit(1)
        )
        mv = latest_snap.market_value_paise if latest_snap else cost
        total_market += mv
        total_cash += acct.cash_balance_paise

        strat = db.get(StrategyModel, acct.strategy_id)
        portfolios.append(PortfolioSummary(
            account_id=acct.id,
            account_code=acct.account_code,
            strategy_name=strat.name if strat else "Unknown",
            status=acct.status,
            inception_date=acct.inception_date,
            holdings_count=len(holdings),
            total_cost_paise=cost,
            market_value_paise=mv,
            cash_balance_paise=acct.cash_balance_paise,
            unrealised_pnl_paise=mv - cost,
        ))

    # Aggregate performance returns (from first active account, or empty)
    returns: list[PerformanceReturn] = []
    if accounts:
        ret_rows = db.scalars(
            select(PerformanceReturnModel)
            .where(PerformanceReturnModel.portfolio_account_id == accounts[0].id)
            .order_by(PerformanceReturnModel.as_of.desc())
        ).all()
        seen_periods: set[str] = set()
        for r in ret_rows:
            if r.period not in seen_periods:
                seen_periods.add(r.period)
                returns.append(PerformanceReturn(
                    period=r.period,
                    twrr_pct=float(r.twrr_pct),
                    mwrr_pct=float(r.mwrr_pct) if r.mwrr_pct is not None else None,
                    benchmark_pct=float(r.benchmark_pct) if r.benchmark_pct is not None else None,
                    as_of=r.as_of,
                ))

    return InvestorDashboard(
        profile=profile,
        portfolios=portfolios,
        total_invested_paise=total_invested,
        total_market_value_paise=total_market,
        total_unrealised_pnl_paise=total_market - total_invested,
        total_cash_paise=total_cash,
        returns=returns,
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

    # Get latest market prices for all securities in this account
    from app.services.market_data import get_latest_prices
    price_map = get_latest_prices(db)

    result = []
    for h in holdings:
        sec = db.get(SecurityModel, h.security_id)
        qty = float(h.quantity)
        cost_val = int(h.avg_cost_paise * qty)
        mkt_price = price_map.get(h.security_id, h.avg_cost_paise)
        mkt_val = int(mkt_price * qty)
        result.append(HoldingDetail(
            security_symbol=sec.symbol if sec else "???",
            security_isin=sec.isin if sec else "???",
            sector=sec.sector if sec else None,
            quantity=qty,
            avg_cost_paise=int(h.avg_cost_paise),
            cost_value_paise=cost_val,
            market_price_paise=mkt_price,
            market_value_paise=mkt_val,
            unrealised_pnl_paise=mkt_val - cost_val,
            day_change_pct=((mkt_val - cost_val) / cost_val * 100) if cost_val else 0.0,
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


@router.get("/valuation-history/{account_id}", response_model=list[ValuationPoint])
def investor_valuation_history(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(_require_investor),
):
    """Valuation history for charting portfolio value over time."""
    subject = user.get("sub", "")
    client = _find_client(db, subject)
    if not client:
        raise NotFoundError("Client record not found")

    acct = db.get(PortfolioAccountModel, account_id)
    if not acct or acct.client_id != client.id:
        raise AuthorizationError("Portfolio account not found or access denied")

    snaps = db.scalars(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == account_id)
        .order_by(ValuationSnapshotModel.as_of.asc())
    ).all()
    return [
        ValuationPoint(
            as_of=s.as_of,
            market_value_paise=s.market_value_paise,
            cost_value_paise=s.cost_value_paise,
            cash_paise=s.cash_paise,
        )
        for s in snaps
    ]


@router.get("/fees/{account_id}", response_model=list[FeeEntry])
def investor_fees(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(_require_investor),
):
    """Fee charges for a portfolio account."""
    subject = user.get("sub", "")
    client = _find_client(db, subject)
    if not client:
        raise NotFoundError("Client record not found")

    acct = db.get(PortfolioAccountModel, account_id)
    if not acct or acct.client_id != client.id:
        raise AuthorizationError("Portfolio account not found or access denied")

    fee_types = {"mgmt_fee", "perf_fee", "exit_load"}
    entries = db.scalars(
        select(CashLedgerModel)
        .where(
            CashLedgerModel.portfolio_account_id == account_id,
            CashLedgerModel.entry_type.in_(fee_types),
        )
        .order_by(CashLedgerModel.posted_on.desc())
        .limit(50)
    ).all()
    return [
        FeeEntry(
            entry_type=e.entry_type,
            amount_paise=abs(e.amount_paise),
            posted_on=e.posted_on,
            description=f"{e.entry_type.replace('_', ' ').title()} charge",
        )
        for e in entries
    ]


@router.get("/documents", response_model=list[DocumentInfo])
def investor_documents(
    db: Session = Depends(get_db),
    user: dict = Depends(_require_investor),
):
    """Documents uploaded during onboarding for this investor."""
    subject = user.get("sub", "")

    # Find application by email
    app = db.scalar(
        select(OnboardingApplicationModel)
        .where(OnboardingApplicationModel.email == subject.lower())
        .order_by(OnboardingApplicationModel.created_at.desc())
    )
    if not app:
        return []

    docs = db.scalars(
        select(OnboardingDocumentModel)
        .where(OnboardingDocumentModel.application_id == app.id)
        .order_by(OnboardingDocumentModel.uploaded_at)
    ).all()

    from app.infrastructure.external.document_storage import get_document_store
    store = get_document_store()

    return [
        DocumentInfo(
            id=d.id,
            document_type=d.document_type,
            uploaded_at=d.uploaded_at.isoformat(),
            download_url=store.get_url(d.storage_key),
        )
        for d in docs
    ]
