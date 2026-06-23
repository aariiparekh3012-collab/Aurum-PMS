"""Performance & analytics endpoints — valuations, returns, snapshots, compute."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.api.v1.dependencies import get_current_user
from app.application.performance.compute import (
    FullComputeCommand,
    FullComputeUseCase,
    ComputeReturnsCommand,
    ComputeReturnsUseCase,
    ComputeSnapshotCommand,
    ComputeSnapshotUseCase,
)
from app.core.database import get_db
from app.infrastructure.db.models_performance import (
    PerformanceReturnModel,
    ValuationSnapshotModel,
)

router = APIRouter(prefix="/performance", tags=["performance"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class SnapshotOut(BaseModel):
    id: uuid.UUID
    portfolio_account_id: uuid.UUID
    as_of: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int

    class Config:
        from_attributes = True


class SnapshotCreate(BaseModel):
    portfolio_account_id: uuid.UUID
    as_of: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int = 0


class ReturnOut(BaseModel):
    id: uuid.UUID
    portfolio_account_id: uuid.UUID
    period: str
    as_of: date
    twrr_pct: float
    benchmark_pct: float | None = None

    class Config:
        from_attributes = True


class ReturnCreate(BaseModel):
    portfolio_account_id: uuid.UUID
    period: str
    as_of: date
    twrr_pct: float
    benchmark_pct: float | None = None


class PortfolioPerformanceSummary(BaseModel):
    latest_market_value_paise: int
    latest_cost_value_paise: int
    latest_cash_paise: int
    unrealised_pnl_paise: int
    unrealised_pnl_pct: float
    returns: list[ReturnOut]
    history: list[SnapshotOut]


class ComputeRequest(BaseModel):
    portfolio_account_id: uuid.UUID
    as_of: date | None = None
    prices: dict[str, int] = {}
    benchmark_pct: float | None = None


class ComputeReturnOut(BaseModel):
    period: str
    as_of: date
    twrr_pct: float
    mwrr_pct: float | None = None
    benchmark_pct: float | None = None
    alpha_pct: float | None = None


class ComputeSnapshotOut(BaseModel):
    id: uuid.UUID
    portfolio_account_id: uuid.UUID
    as_of: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int
    unrealised_pnl_paise: int
    mgmt_fee_accrual_paise: int


class ComputeOut(BaseModel):
    snapshot: ComputeSnapshotOut
    returns: list[ComputeReturnOut]


# ── Compute ───────────────────────────────────────────────────────────────────

@router.post("/compute", response_model=ComputeOut, status_code=201)
def compute_performance(
    body: ComputeRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    as_of = body.as_of or date.today()
    prices = {uuid.UUID(k): v for k, v in body.prices.items()}
    uc = FullComputeUseCase(db)
    result = uc.execute(FullComputeCommand(
        portfolio_account_id=body.portfolio_account_id,
        as_of=as_of,
        prices=prices,
        benchmark_pct=body.benchmark_pct,
    ))
    return ComputeOut(
        snapshot=ComputeSnapshotOut(
            id=result.snapshot.id,
            portfolio_account_id=result.snapshot.portfolio_account_id,
            as_of=result.snapshot.as_of,
            market_value_paise=result.snapshot.market_value_paise,
            cost_value_paise=result.snapshot.cost_value_paise,
            cash_paise=result.snapshot.cash_paise,
            unrealised_pnl_paise=result.snapshot.unrealised_pnl_paise,
            mgmt_fee_accrual_paise=result.snapshot.mgmt_fee_accrual_paise,
        ),
        returns=[
            ComputeReturnOut(
                period=r.period,
                as_of=r.as_of,
                twrr_pct=r.twrr_pct,
                mwrr_pct=r.mwrr_pct,
                benchmark_pct=r.benchmark_pct,
                alpha_pct=r.alpha_pct,
            )
            for r in result.returns
        ],
    )


@router.post("/compute/snapshot", response_model=ComputeSnapshotOut, status_code=201)
def compute_snapshot_only(
    body: ComputeRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Mark holdings to market and record a valuation snapshot without recomputing returns."""
    as_of = body.as_of or date.today()
    prices = {uuid.UUID(k): v for k, v in body.prices.items()}
    uc = ComputeSnapshotUseCase(db)
    snap = uc.execute(ComputeSnapshotCommand(
        portfolio_account_id=body.portfolio_account_id,
        as_of=as_of,
        prices=prices,
    ))
    return ComputeSnapshotOut(
        id=snap.id,
        portfolio_account_id=snap.portfolio_account_id,
        as_of=snap.as_of,
        market_value_paise=snap.market_value_paise,
        cost_value_paise=snap.cost_value_paise,
        cash_paise=snap.cash_paise,
        unrealised_pnl_paise=snap.unrealised_pnl_paise,
        mgmt_fee_accrual_paise=snap.mgmt_fee_accrual_paise,
    )


@router.post("/compute/returns", response_model=list[ComputeReturnOut], status_code=201)
def compute_returns_only(
    body: ComputeRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Recompute period returns from existing snapshots without recording a new snapshot."""
    as_of = body.as_of or date.today()
    uc = ComputeReturnsUseCase(db)
    returns = uc.execute(ComputeReturnsCommand(
        portfolio_account_id=body.portfolio_account_id,
        as_of=as_of,
        benchmark_pct=body.benchmark_pct,
    ))
    return [
        ComputeReturnOut(
            period=r.period,
            as_of=r.as_of,
            twrr_pct=r.twrr_pct,
            mwrr_pct=r.mwrr_pct,
            benchmark_pct=r.benchmark_pct,
            alpha_pct=r.alpha_pct,
        )
        for r in returns
    ]


# ── Raw CRUD ──────────────────────────────────────────────────────────────────

@router.get("/snapshots", response_model=list[SnapshotOut])
def list_snapshots(
    portfolio_account_id: uuid.UUID,
    limit: int = Query(90, le=365),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    stmt = (
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == portfolio_account_id)
        .order_by(desc(ValuationSnapshotModel.as_of))
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.post("/snapshots", response_model=SnapshotOut, status_code=201)
def record_snapshot(
    body: SnapshotCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    snap = ValuationSnapshotModel(
        portfolio_account_id=body.portfolio_account_id,
        as_of=body.as_of,
        market_value_paise=body.market_value_paise,
        cost_value_paise=body.cost_value_paise,
        cash_paise=body.cash_paise,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


@router.get("/returns", response_model=list[ReturnOut])
def list_returns(
    portfolio_account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    stmt = (
        select(PerformanceReturnModel)
        .where(PerformanceReturnModel.portfolio_account_id == portfolio_account_id)
        .order_by(desc(PerformanceReturnModel.as_of))
    )
    return db.scalars(stmt).all()


@router.post("/returns", response_model=ReturnOut, status_code=201)
def record_return(
    body: ReturnCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    ret = PerformanceReturnModel(
        portfolio_account_id=body.portfolio_account_id,
        period=body.period,
        as_of=body.as_of,
        twrr_pct=body.twrr_pct,
        benchmark_pct=body.benchmark_pct,
    )
    db.add(ret)
    db.commit()
    db.refresh(ret)
    return ret


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary/{account_id}", response_model=PortfolioPerformanceSummary)
def performance_summary(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Aggregated performance view for a single portfolio account."""
    latest = db.scalar(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == account_id)
        .order_by(desc(ValuationSnapshotModel.as_of))
        .limit(1)
    )
    mv = latest.market_value_paise if latest else 0
    cv = latest.cost_value_paise if latest else 0
    cash = latest.cash_paise if latest else 0
    pnl = mv - cv
    pnl_pct = round((pnl / cv * 100) if cv > 0 else 0.0, 2)

    returns = db.scalars(
        select(PerformanceReturnModel)
        .where(PerformanceReturnModel.portfolio_account_id == account_id)
        .order_by(desc(PerformanceReturnModel.as_of))
    ).all()

    history = db.scalars(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == account_id)
        .order_by(ValuationSnapshotModel.as_of.asc())
        .limit(90)
    ).all()

    return PortfolioPerformanceSummary(
        latest_market_value_paise=mv,
        latest_cost_value_paise=cv,
        latest_cash_paise=cash,
        unrealised_pnl_paise=pnl,
        unrealised_pnl_pct=pnl_pct,
        returns=returns,
        history=history,
    )
