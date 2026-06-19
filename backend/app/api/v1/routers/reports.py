"""Report generation endpoints -- portfolio statements, transaction reports,
fee invoices, and performance reports.  Returns structured JSON that the
frontend renders and exports to PDF / Excel client-side."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, and_
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models_portfolio import (
    CashLedgerModel,
    FeeScheduleModel,
    HoldingModel,
    PortfolioAccountModel,
)
from app.infrastructure.db.models_trading import TradeModel
from app.infrastructure.db.models_reference import (
    SecurityModel,
    StrategyModel,
    BrokerModel,
)
from app.infrastructure.db.models_performance import (
    PerformanceReturnModel,
    ValuationSnapshotModel,
)

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HoldingRow(BaseModel):
    security_symbol: str
    security_isin: str
    sector: str | None = None
    quantity: float
    avg_cost_paise: int
    market_value_paise: int = 0
    weight_pct: float = 0.0

class CashRow(BaseModel):
    posted_on: date
    entry_type: str
    amount_paise: int
    balance_paise: int

class PortfolioStatementReport(BaseModel):
    account_code: str
    client_id: uuid.UUID
    strategy_name: str
    inception_date: date
    as_of: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int
    unrealised_pnl_paise: int
    holdings: list[HoldingRow]
    cash_ledger: list[CashRow]

class TradeRow(BaseModel):
    traded_at: datetime
    security_symbol: str
    security_isin: str
    side: str
    quantity: float
    price_paise: int
    value_paise: int
    broker_name: str
    contract_note: str | None = None

class TransactionReport(BaseModel):
    account_code: str
    strategy_name: str
    from_date: date
    to_date: date
    total_buy_value_paise: int
    total_sell_value_paise: int
    trade_count: int
    trades: list[TradeRow]

class ReturnRow(BaseModel):
    period: str
    as_of: date
    twrr_pct: float
    benchmark_pct: float | None = None
    alpha_pct: float | None = None

class SnapshotRow(BaseModel):
    as_of: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int

class PerformanceReport(BaseModel):
    account_code: str
    strategy_name: str
    inception_date: date
    latest_market_value_paise: int
    latest_cost_value_paise: int
    unrealised_pnl_paise: int
    returns: list[ReturnRow]
    valuation_history: list[SnapshotRow]

class FeeLineItem(BaseModel):
    description: str
    basis_paise: int
    rate_pct: float
    amount_paise: int

class FeeInvoice(BaseModel):
    account_code: str
    strategy_name: str
    client_id: uuid.UUID
    period_from: date
    period_to: date
    aum_paise: int
    fee_schedule_name: str
    items: list[FeeLineItem]
    total_paise: int
    gst_paise: int
    grand_total_paise: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_account(db: Session, account_id: uuid.UUID, user: dict) -> PortfolioAccountModel:
    """Fetch an account, enforcing that investors may only access their own.

    Returns 404 (not 403) for someone else's account so UUIDs can't be probed."""
    acct = db.get(PortfolioAccountModel, account_id)
    if not acct:
        raise HTTPException(404, "Portfolio account not found")
    client_id = deps.current_client_id(db, user)
    if client_id is not None and acct.client_id != client_id:
        raise HTTPException(404, "Portfolio account not found")
    return acct


def _strategy_name(db: Session, strategy_id: uuid.UUID) -> str:
    s = db.get(StrategyModel, strategy_id)
    return s.name if s else "Unknown"


def _security_map(db: Session) -> dict[uuid.UUID, SecurityModel]:
    secs = db.scalars(select(SecurityModel)).all()
    return {s.id: s for s in secs}


def _broker_map(db: Session) -> dict[uuid.UUID, str]:
    brokers = db.scalars(select(BrokerModel)).all()
    return {b.id: b.name for b in brokers}


# ---------------------------------------------------------------------------
# 1. Portfolio Statement
# ---------------------------------------------------------------------------

@router.get("/portfolio-statement/{account_id}", response_model=PortfolioStatementReport)
def portfolio_statement(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    acct = _get_account(db, account_id, user)
    strat_name = _strategy_name(db, acct.strategy_id)
    sec_map = _security_map(db)

    # Holdings
    holdings_db = db.scalars(
        select(HoldingModel).where(HoldingModel.portfolio_account_id == account_id)
    ).all()

    total_cost = sum(int(h.quantity * h.avg_cost_paise) for h in holdings_db) or 1
    holding_rows = []
    for h in holdings_db:
        sec = sec_map.get(h.security_id)
        cost_val = int(h.quantity * h.avg_cost_paise)
        holding_rows.append(HoldingRow(
            security_symbol=sec.symbol if sec else "???",
            security_isin=sec.isin if sec else "???",
            sector=sec.sector if sec else None,
            quantity=float(h.quantity),
            avg_cost_paise=h.avg_cost_paise,
            market_value_paise=cost_val,
            weight_pct=round(cost_val / total_cost * 100, 2) if total_cost else 0,
        ))

    # Latest snapshot for market value
    latest_snap = db.scalar(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == account_id)
        .order_by(desc(ValuationSnapshotModel.as_of))
        .limit(1)
    )
    mv = latest_snap.market_value_paise if latest_snap else total_cost
    cv = latest_snap.cost_value_paise if latest_snap else total_cost
    cash = latest_snap.cash_paise if latest_snap else 0

    # Cash ledger (last 50 entries)
    cash_rows_db = db.scalars(
        select(CashLedgerModel)
        .where(CashLedgerModel.portfolio_account_id == account_id)
        .order_by(desc(CashLedgerModel.posted_on))
        .limit(50)
    ).all()
    cash_rows = [CashRow(
        posted_on=c.posted_on,
        entry_type=c.entry_type,
        amount_paise=c.amount_paise,
        balance_paise=c.balance_paise,
    ) for c in cash_rows_db]

    return PortfolioStatementReport(
        account_code=acct.account_code,
        client_id=acct.client_id,
        strategy_name=strat_name,
        inception_date=acct.inception_date,
        as_of=date.today(),
        market_value_paise=mv,
        cost_value_paise=cv,
        cash_paise=cash,
        unrealised_pnl_paise=mv - cv,
        holdings=holding_rows,
        cash_ledger=cash_rows,
    )


# ---------------------------------------------------------------------------
# 2. Transaction Report
# ---------------------------------------------------------------------------

@router.get("/transactions/{account_id}", response_model=TransactionReport)
def transaction_report(
    account_id: uuid.UUID,
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    acct = _get_account(db, account_id, user)
    strat_name = _strategy_name(db, acct.strategy_id)
    sec_map = _security_map(db)
    broker_map = _broker_map(db)

    trades_db = db.scalars(
        select(TradeModel)
        .where(and_(
            TradeModel.portfolio_account_id == account_id,
            TradeModel.traded_at >= datetime.combine(from_date, datetime.min.time()),
            TradeModel.traded_at <= datetime.combine(to_date, datetime.max.time()),
        ))
        .order_by(desc(TradeModel.traded_at))
    ).all()

    trade_rows = []
    total_buy = 0
    total_sell = 0
    for t in trades_db:
        sec = sec_map.get(t.security_id)
        val = int(t.quantity * t.price_paise)
        if t.side == "BUY":
            total_buy += val
        else:
            total_sell += val
        trade_rows.append(TradeRow(
            traded_at=t.traded_at,
            security_symbol=sec.symbol if sec else "???",
            security_isin=sec.isin if sec else "???",
            side=t.side,
            quantity=float(t.quantity),
            price_paise=t.price_paise,
            value_paise=val,
            broker_name=broker_map.get(t.broker_id, "Unknown"),
            contract_note=t.contract_note,
        ))

    return TransactionReport(
        account_code=acct.account_code,
        strategy_name=strat_name,
        from_date=from_date,
        to_date=to_date,
        total_buy_value_paise=total_buy,
        total_sell_value_paise=total_sell,
        trade_count=len(trade_rows),
        trades=trade_rows,
    )


# ---------------------------------------------------------------------------
# 3. Performance Report
# ---------------------------------------------------------------------------

@router.get("/performance/{account_id}", response_model=PerformanceReport)
def performance_report(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    acct = _get_account(db, account_id, user)
    strat_name = _strategy_name(db, acct.strategy_id)

    latest_snap = db.scalar(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == account_id)
        .order_by(desc(ValuationSnapshotModel.as_of))
        .limit(1)
    )
    mv = latest_snap.market_value_paise if latest_snap else 0
    cv = latest_snap.cost_value_paise if latest_snap else 0

    returns_db = db.scalars(
        select(PerformanceReturnModel)
        .where(PerformanceReturnModel.portfolio_account_id == account_id)
        .order_by(desc(PerformanceReturnModel.as_of))
    ).all()

    history_db = db.scalars(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == account_id)
        .order_by(ValuationSnapshotModel.as_of.asc())
        .limit(365)
    ).all()

    return PerformanceReport(
        account_code=acct.account_code,
        strategy_name=strat_name,
        inception_date=acct.inception_date,
        latest_market_value_paise=mv,
        latest_cost_value_paise=cv,
        unrealised_pnl_paise=mv - cv,
        returns=[ReturnRow(
            period=r.period,
            as_of=r.as_of,
            twrr_pct=r.twrr_pct,
            benchmark_pct=r.benchmark_pct,
            alpha_pct=round(r.twrr_pct - r.benchmark_pct, 4) if r.benchmark_pct is not None else None,
        ) for r in returns_db],
        valuation_history=[SnapshotRow(
            as_of=s.as_of,
            market_value_paise=s.market_value_paise,
            cost_value_paise=s.cost_value_paise,
            cash_paise=s.cash_paise,
        ) for s in history_db],
    )


# ---------------------------------------------------------------------------
# 4. Fee Invoice
# ---------------------------------------------------------------------------

@router.get("/fee-invoice/{account_id}", response_model=FeeInvoice)
def fee_invoice(
    account_id: uuid.UUID,
    period_from: date = Query(...),
    period_to: date = Query(...),
    db: Session = Depends(get_db),
    user: dict = Depends(deps.get_current_user),
):
    acct = _get_account(db, account_id, user)
    strat_name = _strategy_name(db, acct.strategy_id)

    # AUM = latest market value snapshot in the period
    snap = db.scalar(
        select(ValuationSnapshotModel)
        .where(and_(
            ValuationSnapshotModel.portfolio_account_id == account_id,
            ValuationSnapshotModel.as_of <= period_to,
        ))
        .order_by(desc(ValuationSnapshotModel.as_of))
        .limit(1)
    )
    aum = snap.market_value_paise if snap else 0

    # Fee schedule
    fee_sched = db.get(FeeScheduleModel, acct.fee_schedule_id) if acct.fee_schedule_id else None
    sched_name = fee_sched.name if fee_sched else "Standard"
    mgmt_pct = float(fee_sched.mgmt_fee_pct) if fee_sched else 2.0
    perf_pct = float(fee_sched.perf_fee_pct) if fee_sched else 20.0

    # Prorate management fee for the period
    days = (period_to - period_from).days or 1
    mgmt_fee = int(aum * mgmt_pct / 100 * days / 365)

    # Performance fee (simplified: on unrealised gains in the period)
    snap_start = db.scalar(
        select(ValuationSnapshotModel)
        .where(and_(
            ValuationSnapshotModel.portfolio_account_id == account_id,
            ValuationSnapshotModel.as_of >= period_from,
        ))
        .order_by(ValuationSnapshotModel.as_of.asc())
        .limit(1)
    )
    start_mv = snap_start.market_value_paise if snap_start else aum
    gain = max(0, aum - start_mv)
    perf_fee = int(gain * perf_pct / 100)

    items = [
        FeeLineItem(
            description="Management fee (pro-rated {days}d)".format(days=days),
            basis_paise=aum,
            rate_pct=mgmt_pct,
            amount_paise=mgmt_fee,
        ),
    ]
    if perf_fee > 0:
        items.append(FeeLineItem(
            description="Performance fee on gains",
            basis_paise=gain,
            rate_pct=perf_pct,
            amount_paise=perf_fee,
        ))

    subtotal = mgmt_fee + perf_fee
    gst = int(subtotal * 0.18)

    return FeeInvoice(
        account_code=acct.account_code,
        strategy_name=strat_name,
        client_id=acct.client_id,
        period_from=period_from,
        period_to=period_to,
        aum_paise=aum,
        fee_schedule_name=sched_name,
        items=items,
        total_paise=subtotal,
        gst_paise=gst,
        grand_total_paise=subtotal + gst,
    )


# ---------------------------------------------------------------------------
# 5. Available reports list (for frontend dropdown)
# ---------------------------------------------------------------------------

@router.get("/types")
def report_types(_user: dict = Depends(deps.get_current_user)):
    return [
        {"key": "portfolio_statement", "label": "Portfolio Statement", "description": "Current holdings, valuations, and cash ledger"},
        {"key": "transaction_report", "label": "Transaction Report", "description": "Trade history for a date range"},
        {"key": "performance_report", "label": "Performance Report", "description": "Returns, benchmarks, and valuation history"},
        {"key": "fee_invoice", "label": "Fee Invoice", "description": "Management and performance fee calculation"},
    ]
