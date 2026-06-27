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
    FeeScheduleModel, PortfolioAccountModel, HoldingModel, CashLedgerModel,
)
from app.infrastructure.db.models_reference import SecurityModel, StrategyModel
from app.services.market_data import get_latest_prices
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
    code: str = ""
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
        # Staff with no client_id filter → return all accounts
        from sqlalchemy import select
        all_accts = db.scalars(select(PortfolioAccountModel)).all()
        return [
            {
                "id": str(a.id), "account_code": a.account_code,
                "strategy_id": str(a.strategy_id),
                "client_id": str(a.client_id),
                "status": a.status,
                "inception_date": str(a.inception_date),
                "cash_balance_inr": a.cash_balance_paise / 100,
                "holdings_count": 0,
            }
            for a in all_accts
        ]

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

    # Fetch latest market prices for LTP / P&L
    prices = get_latest_prices(db)

    result = []
    for sec_id, holding in account.holdings.items():
        sec = db.get(SecurityModel, sec_id)
        ltp_paise = prices.get(sec_id)
        avg_cost_paise = holding.avg_cost_paise
        qty = holding.quantity
        total_cost_paise = avg_cost_paise * qty
        current_value_paise = (ltp_paise * qty) if ltp_paise else None
        pnl_paise = (current_value_paise - total_cost_paise) if current_value_paise is not None else None
        pnl_pct = (pnl_paise / total_cost_paise * 100) if (pnl_paise is not None and total_cost_paise) else None

        result.append({
            "security_id": str(sec_id),
            "isin": sec.isin if sec else "",
            "symbol": sec.symbol if sec else "",
            "name": sec.symbol if sec else "",
            "sector": sec.sector if sec else "",
            "quantity": qty,
            "avg_cost_paise": avg_cost_paise,
            "avg_cost_inr": avg_cost_paise / 100,
            "total_cost_inr": total_cost_paise / 100,
            "ltp_paise": ltp_paise,
            "ltp_inr": ltp_paise / 100 if ltp_paise else None,
            "current_value_inr": current_value_paise / 100 if current_value_paise is not None else None,
            "pnl_inr": pnl_paise / 100 if pnl_paise is not None else None,
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
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
    db.flush()
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
    code = body.code or body.name.upper().replace(" ", "_")[:32]
    strat = StrategyModel(name=body.name, code=code, approach=body.approach)
    db.add(strat)
    db.flush()
    return {"id": str(strat.id), "name": strat.name, "code": strat.code}


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
        if body.balance_paise is not None:
            # Explicit balance override (for seeding / corrections only)
            account.cash_balance_paise = body.balance_paise
        else:
            # Normal flow: adjust the running balance by the entry amount
            account.cash_balance_paise += body.amount_paise
    db.flush()
    new_balance = account.cash_balance_paise if account else body.amount_paise
    return {"id": str(entry.id), "entry_type": body.entry_type, "balance_inr": new_balance / 100}


# ── Fee schedules ──────────────────────────────────────────────────────────

class FeeScheduleOut(BaseModel):
    id: uuid.UUID
    name: str
    mgmt_fee_pct: float
    perf_fee_pct: float
    high_water_mark: bool
    hurdle_rate_pct: float | None = None

    class Config:
        from_attributes = True


class CreateFeeScheduleRequest(BaseModel):
    name: str
    mgmt_fee_pct: float = Field(ge=0)
    perf_fee_pct: float = Field(ge=0, default=0)
    high_water_mark: bool = False
    hurdle_rate_pct: float | None = None


@router.get("/fee-schedules", response_model=list[FeeScheduleOut])
def list_fee_schedules(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    rows = db.query(FeeScheduleModel).all()
    return rows


@router.post("/fee-schedules", response_model=FeeScheduleOut, status_code=201)
def create_fee_schedule(
    body: CreateFeeScheduleRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_role("compliance")),
):
    sched = FeeScheduleModel(
        name=body.name,
        mgmt_fee_pct=body.mgmt_fee_pct,
        perf_fee_pct=body.perf_fee_pct,
        high_water_mark=body.high_water_mark,
        hurdle_rate_pct=body.hurdle_rate_pct,
    )
    db.add(sched)
    db.flush()
    db.refresh(sched)
    return sched
