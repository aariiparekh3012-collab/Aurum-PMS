"""Performance & analytics endpoints -- valuations, returns, snapshots."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models_performance import (
    PerformanceReturnModel,
    ValuationSnapshotModel,
)

router = APIRouter(prefix="/performance", tags=["performance"])


# -- Schemas -----------------------------------------------------------------

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
    returns: list[ReturnOut]
    history: list[SnapshotOut]


# -- Snapshots ---------------------------------------------------------------

@router.get("/snapshots", response_model=list[SnapshotOut])
def list_snapshots(
    portfolio_account_id: uuid.UUID,
    limit: int = Query(90, le=365),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
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


# -- Returns -----------------------------------------------------------------

@router.get("/returns", response_model=list[ReturnOut])
def list_returns(
    portfolio_account_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
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


# -- Summary -----------------------------------------------------------------

@router.get("/summary/{account_id}", response_model=PortfolioPerformanceSummary)
def performance_summary(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Aggregated performance view for a single portfolio account."""
    # Latest snapshot
    latest = db.scalar(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == account_id)
        .order_by(desc(ValuationSnapshotModel.as_of))
        .limit(1)
    )
    mv = latest.market_value_paise if latest else 0
    cv = latest.cost_value_paise if latest else 0
    cash = latest.cash_paise if latest else 0

    # Returns
    returns = db.scalars(
        select(PerformanceReturnModel)
        .where(PerformanceReturnModel.portfolio_account_id == account_id)
        .order_by(desc(PerformanceReturnModel.as_of))
    ).all()

    # History (last 90 days)
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
        unrealised_pnl_paise=mv - cv,
        returns=returns,
        history=history,
    )
