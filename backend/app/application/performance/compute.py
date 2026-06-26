"""Application-layer orchestration for performance computation.

Reads portfolio state from the DB, runs the domain engine, and persists
the results back as ValuationSnapshot + PerformanceReturn rows.

This is intentionally the only place that touches both the portfolio and
performance DB tables together.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.performance.engine import (
    CashFlow,
    FeeSchedule,
    ValuationPoint,
    compute_mgmt_fee,
    compute_mwrr,
    compute_period_returns,
)
from app.infrastructure.db.models_performance import (
    PerformanceReturnModel,
    ValuationSnapshotModel,
)
from app.infrastructure.db.models_portfolio import (
    CapitalFlowModel,
    FeeScheduleModel,
    HoldingModel,
    PortfolioAccountModel,
)


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class ComputeSnapshotCommand:
    portfolio_account_id: uuid.UUID
    as_of: date
    # Market prices keyed by security_id (paise per share).
    # If empty, cost price is used as a proxy (i.e. no mark-to-market).
    prices: dict[uuid.UUID, int]


@dataclass
class ComputeReturnsCommand:
    portfolio_account_id: uuid.UUID
    as_of: date
    benchmark_pct: float | None = None  # optional benchmark value to store


@dataclass
class SnapshotView:
    id: uuid.UUID
    portfolio_account_id: uuid.UUID
    as_of: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int
    unrealised_pnl_paise: int
    mgmt_fee_accrual_paise: int


@dataclass
class ReturnView:
    period: str
    as_of: date
    twrr_pct: float
    mwrr_pct: float | None
    benchmark_pct: float | None
    alpha_pct: float | None


@dataclass
class FullComputeCommand:
    """Run snapshot + returns in one call (most common path)."""
    portfolio_account_id: uuid.UUID
    as_of: date
    prices: dict[uuid.UUID, int]
    benchmark_pct: float | None = None


@dataclass
class FullComputeView:
    snapshot: SnapshotView
    returns: list[ReturnView]


# ── Use cases ─────────────────────────────────────────────────────────────────

class ComputeSnapshotUseCase:
    """Snapshot: mark all holdings to market, accrue management fee, persist."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def execute(self, cmd: ComputeSnapshotCommand) -> SnapshotView:
        db = self._db
        account = db.get(PortfolioAccountModel, cmd.portfolio_account_id)
        if account is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"Portfolio account {cmd.portfolio_account_id} not found")

        # ── Mark holdings to market ───────────────────────────────────────
        holdings = (
            db.query(HoldingModel)
            .filter_by(portfolio_account_id=cmd.portfolio_account_id)
            .all()
        )
        market_value_paise = 0
        cost_value_paise = 0
        for h in holdings:
            price = cmd.prices.get(h.security_id, h.avg_cost_paise)
            market_value_paise += int(h.quantity * price)
            cost_value_paise += int(h.quantity * h.avg_cost_paise)

        cash_paise = account.cash_balance_paise

        # ── Management fee accrual (daily) ────────────────────────────────
        mgmt_fee = 0
        if account.fee_schedule_id:
            fs = db.get(FeeScheduleModel, account.fee_schedule_id)
            if fs:
                schedule = FeeSchedule(
                    mgmt_fee_pct=float(fs.mgmt_fee_pct),
                    perf_fee_pct=float(fs.perf_fee_pct),
                    high_water_mark=fs.high_water_mark,
                    hurdle_rate_pct=float(fs.hurdle_rate_pct or 0),
                )
                aum = market_value_paise + cash_paise
                mgmt_fee = compute_mgmt_fee(aum, schedule, days=1)

        # ── Upsert snapshot ───────────────────────────────────────────────
        existing = db.scalar(
            select(ValuationSnapshotModel)
            .where(
                ValuationSnapshotModel.portfolio_account_id == cmd.portfolio_account_id,
                ValuationSnapshotModel.as_of == cmd.as_of,
            )
        )
        if existing:
            existing.market_value_paise = market_value_paise
            existing.cost_value_paise = cost_value_paise
            existing.cash_paise = cash_paise
            snap = existing
        else:
            snap = ValuationSnapshotModel(
                portfolio_account_id=cmd.portfolio_account_id,
                as_of=cmd.as_of,
                market_value_paise=market_value_paise,
                cost_value_paise=cost_value_paise,
                cash_paise=cash_paise,
            )
            db.add(snap)

        db.flush()

        return SnapshotView(
            id=snap.id,
            portfolio_account_id=snap.portfolio_account_id,
            as_of=snap.as_of,
            market_value_paise=market_value_paise,
            cost_value_paise=cost_value_paise,
            cash_paise=cash_paise,
            unrealised_pnl_paise=market_value_paise - cost_value_paise,
            mgmt_fee_accrual_paise=mgmt_fee,
        )


class ComputeReturnsUseCase:
    """Compute and persist TWRR + MWRR for all standard periods."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def execute(self, cmd: ComputeReturnsCommand) -> list[ReturnView]:
        db = self._db
        account = db.get(PortfolioAccountModel, cmd.portfolio_account_id)
        if account is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"Portfolio account {cmd.portfolio_account_id} not found")

        # ── Load all snapshots ────────────────────────────────────────────
        snaps = db.scalars(
            select(ValuationSnapshotModel)
            .where(ValuationSnapshotModel.portfolio_account_id == cmd.portfolio_account_id)
            .order_by(ValuationSnapshotModel.as_of)
        ).all()

        valuations = [
            ValuationPoint(
                date=s.as_of,
                market_value_paise=s.market_value_paise,
                cost_value_paise=s.cost_value_paise,
                cash_paise=s.cash_paise,
            )
            for s in snaps
        ]

        # ── Load capital flows ────────────────────────────────────────────
        flows_raw = db.scalars(
            select(CapitalFlowModel)
            .where(CapitalFlowModel.portfolio_account_id == cmd.portfolio_account_id)
            .order_by(CapitalFlowModel.value_date)
        ).all()

        cash_flows = [
            CashFlow(
                date=f.value_date,
                # contributions positive, withdrawals negative
                amount_paise=f.amount_paise if f.flow_type == "contribution" else -f.amount_paise,
            )
            for f in flows_raw
        ]

        if not valuations:
            return []

        inception_date = account.inception_date
        period_results = compute_period_returns(valuations, cash_flows, cmd.as_of, inception_date)

        # MWRR (since inception only — computationally expensive)
        inception_snap = snaps[0] if snaps else None
        latest_snap = snaps[-1] if snaps else None
        mwrr_si: float | None = None
        if inception_snap and latest_snap and inception_snap.as_of != latest_snap.as_of:
            mwrr_si = compute_mwrr(
                inception_value_paise=inception_snap.total_value_paise if hasattr(inception_snap, 'total_value_paise')
                    else inception_snap.market_value_paise + inception_snap.cash_paise,
                inception_date=inception_snap.as_of,
                cash_flows=cash_flows,
                terminal_value_paise=latest_snap.market_value_paise + latest_snap.cash_paise,
                terminal_date=latest_snap.as_of,
            )
            if mwrr_si is not None:
                mwrr_si = round(mwrr_si * 100, 4)

        # ── Upsert PerformanceReturn rows ─────────────────────────────────
        views: list[ReturnView] = []
        for pr in period_results:
            existing = db.scalar(
                select(PerformanceReturnModel).where(
                    PerformanceReturnModel.portfolio_account_id == cmd.portfolio_account_id,
                    PerformanceReturnModel.period == pr.period,
                    PerformanceReturnModel.as_of == pr.as_of,
                )
            )
            mwrr = mwrr_si if pr.period == "SI" else None
            if existing:
                existing.twrr_pct = pr.twrr_pct
                existing.mwrr_pct = mwrr if pr.period == "SI" else None
                existing.benchmark_pct = cmd.benchmark_pct
            else:
                row = PerformanceReturnModel(
                    portfolio_account_id=cmd.portfolio_account_id,
                    period=pr.period,
                    as_of=pr.as_of,
                    twrr_pct=pr.twrr_pct,
                    mwrr_pct=mwrr if pr.period == "SI" else None,
                    benchmark_pct=cmd.benchmark_pct,
                )
                db.add(row)

            bm = cmd.benchmark_pct
            views.append(ReturnView(
                period=pr.period,
                as_of=pr.as_of,
                twrr_pct=pr.twrr_pct,
                mwrr_pct=mwrr,
                benchmark_pct=bm,
                alpha_pct=round(pr.twrr_pct - bm, 4) if bm is not None else None,
            ))

        db.flush()
        return views


class FullComputeUseCase:
    """Snapshot + returns in one transactional call."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def execute(self, cmd: FullComputeCommand) -> FullComputeView:
        snap = ComputeSnapshotUseCase(self._db).execute(
            ComputeSnapshotCommand(
                portfolio_account_id=cmd.portfolio_account_id,
                as_of=cmd.as_of,
                prices=cmd.prices,
            )
        )
        returns = ComputeReturnsUseCase(self._db).execute(
            ComputeReturnsCommand(
                portfolio_account_id=cmd.portfolio_account_id,
                as_of=cmd.as_of,
                benchmark_pct=cmd.benchmark_pct,
            )
        )
        return FullComputeView(snapshot=snap, returns=returns)
