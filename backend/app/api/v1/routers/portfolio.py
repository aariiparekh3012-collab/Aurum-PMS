"""Portfolio API endpoints — accounts, trades, holdings, capital flows."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.api.v1.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.infrastructure.db.models_portfolio import (
    PortfolioAccountModel, HoldingModel, CashLedgerModel,
)
from app.infrastructure.db.models_reference import SecurityModel, StrategyModel
from app.infrastructure.db.portfolio_repository import (
    SqlAlchemyClientRepository, SqlAlchemyPortfolioAccountRepository,
    SqlAlchemyTradeRepository,
)
from app.infrastructure.db.repository import SqlAlchemyOnboardingRepository
from app.application.portfolio.use_cases.provision_client import ProvisionClientUseCase
from app.application.portfolio.use_cases.create_portfolio import CreatePortfolioUseCase
from app.application.portfolio.use_cases.record_trade import RecordTradeUseCase
from app.application.portfolio.use_cases.record_capital_flow import RecordCapitalFlowUseCase
from app.application.portfolio.dto import (
    ProvisionClientCommand, CreatePortfolioCommand,
    RecordTradeCommand, CapitalFlowCommand,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ── Access control helpers ──────────────────────────────────────────────
# Staff (compliance/RM) may read any account. Investors are scoped to the
# client record that matches their JWT subject (email). The shared resolver
# (deps.current_client_id) lives in app.api.dependencies so every router
# enforces ownership identically.

def _assert_account_access(db: Session, user: dict, account_id: uuid.UUID) -> None:
    """Allow staff; for investors require the account to belong to them.

    Uses 404 (not 403) so account UUIDs can't be probed for existence."""
    client_id = deps.current_client_id(db, user)
    if client_id is None:
        return
    acct = db.get(PortfolioAccountModel, account_id)
    if acct is None or acct.client_id != client_id:
        raise HTTPException(404, "Portfolio account not found")


# ── Request schemas ─────────────────────────────────────────────────────

class ProvisionClientRequest(BaseModel):
    onboarding_application_id: uuid.UUID

class CreatePortfolioRequest(BaseModel):
    client_id: uuid.UUID
    strategy_id: uuid.UUID
    fee_schedule_id: uuid.UUID | None = None

class RecordTradeRequest(BaseModel):
    security_id: uuid.UUID
    side: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)
    price_inr: float = Field(gt=0)

class CapitalFlowRequest(BaseModel):
    flow_type: str = Field(pattern="^(contribution|withdrawal)$")
    amount_inr: float = Field(gt=0)

class SecuritySeedRequest(BaseModel):
    isin: str = Field(min_length=12, max_length=12)
    symbol: str
    name: str
    exchange: str = "NSE"
    instrument_type: str = "equity"
    sector: str = ""

class StrategySeedRequest(BaseModel):
    name: str
    approach: str = "discretionary"


# ── Client provisioning ────────────────────────────────────────────────

@router.post("/clients/provision", status_code=201)
def provision_client(
    body: ProvisionClientRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    uc = ProvisionClientUseCase(
        onboarding_repo=SqlAlchemyOnboardingRepository(db),
        client_repo=SqlAlchemyClientRepository(db),
    )
    view = uc.execute(ProvisionClientCommand(
        onboarding_application_id=body.onboarding_application_id,
    ))
    return {
        "id": str(view.id), "client_code": view.client_code,
        "full_name": view.full_name, "email": view.email,
        "investor_type": view.investor_type, "status": view.status,
    }


@router.get("/clients")
def list_clients(
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    repo = SqlAlchemyClientRepository(db)
    clients = repo.list_all()
    return {
        "clients": [
            {
                "id": str(c.id), "client_code": c.client_code,
                "full_name": c.full_name, "email": c.email,
                "investor_type": c.investor_type, "status": c.status.value,
            }
            for c in clients
        ]
    }


# ── Portfolio accounts ──────────────────────────────────────────────────

@router.post("/accounts", status_code=201)
def create_portfolio_account(
    body: CreatePortfolioRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    uc = CreatePortfolioUseCase(
        client_repo=SqlAlchemyClientRepository(db),
        portfolio_repo=SqlAlchemyPortfolioAccountRepository(db),
    )
    view = uc.execute(CreatePortfolioCommand(
        client_id=body.client_id,
        strategy_id=body.strategy_id,
        fee_schedule_id=body.fee_schedule_id,
    ))
    return {
        "id": str(view.id), "account_code": view.account_code,
        "status": view.status, "inception_date": view.inception_date,
    }


@router.get("/accounts/{account_id}")
def get_portfolio_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_account_access(db, user, account_id)
    repo = SqlAlchemyPortfolioAccountRepository(db)
    account = repo.get(account_id)
    if account is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Portfolio account not found")

    # Lookup strategy name
    strategy = db.get(StrategyModel, account.strategy_id)
    strategy_name = strategy.name if strategy else ""

    return {
        "id": str(account.id), "account_code": account.account_code,
        "strategy_name": strategy_name,
        "status": account.status.value,
        "inception_date": str(account.inception_date),
        "cash_balance_inr": account.cash_balance_paise / 100,
        "invested_value_inr": account.total_cost_paise / 100,
        "holdings_count": len(account.holdings),
    }


@router.get("/accounts")
def list_portfolios_by_client(
    client_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    own_client_id = deps.current_client_id(db, user)
    if own_client_id is not None:
        # Investors are always scoped to their own client, regardless of the param.
        client_id = own_client_id
    elif client_id is None:
        raise HTTPException(400, "client_id is required")

    repo = SqlAlchemyPortfolioAccountRepository(db)
    accounts = repo.list_by_client(client_id)
    return {
        "accounts": [
            {
                "id": str(a.id), "account_code": a.account_code,
                "status": a.status.value,
                "inception_date": str(a.inception_date),
                "cash_balance_inr": a.cash_balance_paise / 100,
                "holdings_count": len(a.holdings),
            }
            for a in accounts
        ]
    }


# ── Holdings ────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/holdings")
def get_holdings(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_account_access(db, user, account_id)
    repo = SqlAlchemyPortfolioAccountRepository(db)
    account = repo.get(account_id)
    if account is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Portfolio account not found")

    result = []
    for sec_id, holding in account.holdings.items():
        sec = db.get(SecurityModel, sec_id)
        result.append({
            "security_id": str(sec_id),
            "isin": sec.isin if sec else "",
            "symbol": sec.symbol if sec else "",
            "name": sec.symbol if sec else "",
            "quantity": holding.quantity,
            "avg_cost_inr": holding.avg_cost_paise / 100,
            "total_cost_inr": holding.total_cost_paise / 100,
            "lots_count": len(holding.lots),
        })
    return {"account_id": str(account_id), "holdings": result}


# ── Trades ──────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/trades", status_code=201)
def record_trade(
    account_id: uuid.UUID,
    body: RecordTradeRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    uc = RecordTradeUseCase(
        portfolio_repo=SqlAlchemyPortfolioAccountRepository(db),
        trade_repo=SqlAlchemyTradeRepository(db),
    )
    view = uc.execute(RecordTradeCommand(
        portfolio_account_id=account_id,
        security_id=body.security_id,
        side=body.side,
        quantity=body.quantity,
        price_inr=body.price_inr,
    ))
    return {
        "id": str(view.id), "side": view.side,
        "quantity": view.quantity, "price_inr": view.price_inr,
        "value_inr": view.value_inr, "traded_at": view.traded_at,
    }


@router.get("/accounts/{account_id}/trades")
def list_trades(
    account_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_account_access(db, user, account_id)
    repo = SqlAlchemyTradeRepository(db)
    trades = repo.list_by_portfolio(account_id, limit=limit)
    result = []
    for t in trades:
        sec = db.get(SecurityModel, t.security_id)
        result.append({
            "id": str(t.id), "side": t.side.value,
            "security_name": sec.symbol if sec else "",
            "symbol": sec.symbol if sec else "",
            "quantity": t.quantity, "price_inr": t.price_paise / 100,
            "value_inr": t.value_paise / 100,
            "traded_at": t.traded_at.isoformat(),
        })
    return {"account_id": str(account_id), "trades": result}


# ── Capital flows ───────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/capital-flows", status_code=201)
def record_capital_flow(
    account_id: uuid.UUID,
    body: CapitalFlowRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    uc = RecordCapitalFlowUseCase(
        portfolio_repo=SqlAlchemyPortfolioAccountRepository(db),
    )
    result = uc.execute(CapitalFlowCommand(
        portfolio_account_id=account_id,
        flow_type=body.flow_type,
        amount_inr=body.amount_inr,
    ))
    return result


@router.get("/accounts/{account_id}/cash-ledger")
def get_cash_ledger(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _assert_account_access(db, user, account_id)
    rows = (
        db.query(CashLedgerModel)
        .filter_by(portfolio_account_id=account_id)
        .order_by(CashLedgerModel.posted_on.desc())
        .limit(100)
        .all()
    )
    return {
        "account_id": str(account_id),
        "entries": [
            {
                "entry_type": r.entry_type,
                "amount_inr": r.amount_paise / 100,
                "posted_on": str(r.posted_on),
                "description": r.description,
            }
            for r in rows
        ],
    }


# ── Reference data seeding (dev/demo) ──────────────────────────────────

@router.post("/securities", status_code=201)
def seed_security(
    body: SecuritySeedRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    sec = SecurityModel(
        isin=body.isin, symbol=body.symbol,
        exchange=body.exchange, instrument_type=body.instrument_type,
        sector=body.sector,
    )
    db.add(sec)
    return {"id": str(sec.id), "isin": sec.isin, "symbol": sec.symbol}


@router.get("/securities")
def list_securities(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    rows = db.query(SecurityModel).filter_by(is_active=True).all()
    return {
        "securities": [
            {"id": str(r.id), "isin": r.isin, "symbol": r.symbol, "name": r.symbol, "sector": r.sector}
            for r in rows
        ]
    }


@router.post("/strategies", status_code=201)
def seed_strategy(
    body: StrategySeedRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    strat = StrategyModel(name=body.name, approach=body.approach)
    db.add(strat)
    return {"id": str(strat.id), "name": strat.name}


@router.get("/strategies")
def list_strategies(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    rows = db.query(StrategyModel).filter_by(is_active=True).all()
    return {
        "strategies": [
            {"id": str(r.id), "name": r.name, "approach": r.approach}
            for r in rows
        ]
    }


# ── Holdings / cash write endpoints (used by seed + RM tools) ───────────────

class AddHoldingRequest(BaseModel):
    security_id: uuid.UUID
    quantity: float = Field(gt=0)
    avg_cost_paise: int = Field(ge=0)


@router.post("/accounts/{account_id}/holdings", status_code=201)
def add_holding(
    account_id: uuid.UUID,
    body: AddHoldingRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    existing = (
        db.query(HoldingModel)
        .filter_by(portfolio_account_id=account_id, security_id=body.security_id)
        .first()
    )
    if existing is not None:
        existing.quantity = body.quantity
        existing.avg_cost_paise = body.avg_cost_paise
        holding = existing
    else:
        holding = HoldingModel(
            portfolio_account_id=account_id,
            security_id=body.security_id,
            quantity=body.quantity,
            avg_cost_paise=body.avg_cost_paise,
        )
        db.add(holding)
    db.flush()
    return {
        "id": str(holding.id),
        "security_id": str(body.security_id),
        "quantity": body.quantity,
        "avg_cost_inr": body.avg_cost_paise / 100,
    }


class AddCashEntryRequest(BaseModel):
    entry_type: str
    amount_paise: int
    balance_paise: int | None = None
    posted_on: str | None = None
    description: str = ""


@router.post("/accounts/{account_id}/cash", status_code=201)
def add_cash_entry(
    account_id: uuid.UUID,
    body: AddCashEntryRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance", "relationship_manager")),
):
    import datetime as _dt

    posted = (
        _dt.date.fromisoformat(body.posted_on) if body.posted_on else _dt.date.today()
    )
    balance = body.balance_paise if body.balance_paise is not None else body.amount_paise
    entry = CashLedgerModel(
        portfolio_account_id=account_id,
        entry_type=body.entry_type,
        amount_paise=body.amount_paise,
        balance_paise=balance,
        posted_on=posted,
        description=body.description,
    )
    db.add(entry)
    # keep the account's running cash balance in sync for dashboards
    account = db.get(PortfolioAccountModel, account_id)
    if account is not None:
        account.cash_balance_paise = balance
    db.flush()
    return {"id": str(entry.id), "entry_type": body.entry_type, "balance_inr": balance / 100}
