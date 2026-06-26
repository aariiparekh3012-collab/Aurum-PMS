"""Fee engine — compute and charge PMS fees to portfolio cash ledgers.

Fee types handled:
  1. Management fee  — % of AUM, accrued daily, charged quarterly
  2. Performance fee — % of gains above HWM + hurdle, charged annually
  3. Exit load        — % of withdrawal amount, charged on capital outflows

All amounts are in paise. Fee debits create cash_ledger entries and reduce
the portfolio account's cash_balance_paise.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select, desc, and_
from sqlalchemy.orm import Session

from app.domain.performance.engine import FeeSchedule, compute_mgmt_fee, compute_perf_fee
from app.infrastructure.db.models_performance import ValuationSnapshotModel
from app.infrastructure.db.models_portfolio import (
    CashLedgerModel,
    FeeScheduleModel,
    PortfolioAccountModel,
)

logger = logging.getLogger(__name__)


# ── Models for fee tracking ──────────────────────────────────────────────────

@dataclass
class FeeChargeResult:
    portfolio_account_id: uuid.UUID
    account_code: str
    mgmt_fee_paise: int
    perf_fee_paise: int
    total_fee_paise: int
    new_cash_balance_paise: int


@dataclass
class ExitLoadResult:
    portfolio_account_id: uuid.UUID
    withdrawal_paise: int
    exit_load_paise: int
    net_withdrawal_paise: int


# ── Fee schedule helper ──────────────────────────────────────────────────────

# Default exit load: 1% if redeemed within 1 year, 0% after.
DEFAULT_EXIT_LOAD_PCT = 1.0
EXIT_LOAD_WAIVER_DAYS = 365


def _get_fee_schedule(db: Session, account: PortfolioAccountModel) -> FeeSchedule | None:
    if not account.fee_schedule_id:
        return None
    fs = db.get(FeeScheduleModel, account.fee_schedule_id)
    if fs is None:
        return None
    return FeeSchedule(
        mgmt_fee_pct=float(fs.mgmt_fee_pct),
        perf_fee_pct=float(fs.perf_fee_pct),
        high_water_mark=fs.high_water_mark,
        hurdle_rate_pct=float(fs.hurdle_rate_pct or 0),
    )


# ── Management fee billing ───────────────────────────────────────────────────

def charge_management_fee(
    db: Session,
    portfolio_account_id: uuid.UUID,
    as_of: dt.date | None = None,
    days: int = 90,
) -> FeeChargeResult | None:
    """Compute and charge management fee for the given period (default quarterly).

    The fee is calculated as: AUM × (annual_rate / 365) × days.
    AUM = latest market_value + cash at the most recent snapshot.
    """
    if as_of is None:
        as_of = dt.date.today()

    account = db.get(PortfolioAccountModel, portfolio_account_id)
    if account is None:
        return None

    schedule = _get_fee_schedule(db, account)
    if schedule is None or schedule.mgmt_fee_pct <= 0:
        return FeeChargeResult(
            portfolio_account_id=account.id,
            account_code=account.account_code,
            mgmt_fee_paise=0, perf_fee_paise=0, total_fee_paise=0,
            new_cash_balance_paise=account.cash_balance_paise,
        )

    # Get latest AUM from valuation snapshot
    latest_snap = db.scalar(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == portfolio_account_id)
        .order_by(desc(ValuationSnapshotModel.as_of))
        .limit(1)
    )

    if latest_snap is None:
        # No valuation data — can't compute fee
        return None

    aum_paise = latest_snap.market_value_paise + latest_snap.cash_paise
    fee = compute_mgmt_fee(aum_paise, schedule, days=days)

    if fee > 0:
        _debit_fee(db, account, fee, as_of, "mgmt_fee", f"Management fee ({days}d)")

    return FeeChargeResult(
        portfolio_account_id=account.id,
        account_code=account.account_code,
        mgmt_fee_paise=fee,
        perf_fee_paise=0,
        total_fee_paise=fee,
        new_cash_balance_paise=account.cash_balance_paise,
    )


# ── Performance fee billing ──────────────────────────────────────────────────

def charge_performance_fee(
    db: Session,
    portfolio_account_id: uuid.UUID,
    as_of: dt.date | None = None,
) -> FeeChargeResult | None:
    """Compute and charge performance fee with high-water mark logic.

    Typically run annually. The HWM is tracked via the highest historical
    valuation snapshot.
    """
    if as_of is None:
        as_of = dt.date.today()

    account = db.get(PortfolioAccountModel, portfolio_account_id)
    if account is None:
        return None

    schedule = _get_fee_schedule(db, account)
    if schedule is None or schedule.perf_fee_pct <= 0:
        return FeeChargeResult(
            portfolio_account_id=account.id,
            account_code=account.account_code,
            mgmt_fee_paise=0, perf_fee_paise=0, total_fee_paise=0,
            new_cash_balance_paise=account.cash_balance_paise,
        )

    # Get all snapshots to find HWM
    snapshots = db.scalars(
        select(ValuationSnapshotModel)
        .where(ValuationSnapshotModel.portfolio_account_id == portfolio_account_id)
        .order_by(ValuationSnapshotModel.as_of)
    ).all()

    if len(snapshots) < 2:
        return None

    # HWM = max total value across all previous snapshots
    hwm_paise = max(
        s.market_value_paise + s.cash_paise
        for s in snapshots[:-1]  # exclude the latest
    )

    latest = snapshots[-1]
    current_value = latest.market_value_paise + latest.cash_paise

    # Days since inception for hurdle calculation
    period_days = (latest.as_of - snapshots[0].as_of).days or 365

    fee, new_hwm = compute_perf_fee(
        current_value_paise=current_value,
        high_water_mark_paise=hwm_paise,
        fee_schedule=schedule,
        period_days=period_days,
    )

    if fee > 0:
        _debit_fee(db, account, fee, as_of, "perf_fee", "Performance fee (annual)")

    return FeeChargeResult(
        portfolio_account_id=account.id,
        account_code=account.account_code,
        mgmt_fee_paise=0,
        perf_fee_paise=fee,
        total_fee_paise=fee,
        new_cash_balance_paise=account.cash_balance_paise,
    )


# ── Exit load ────────────────────────────────────────────────────────────────

def compute_exit_load(
    db: Session,
    portfolio_account_id: uuid.UUID,
    withdrawal_paise: int,
    exit_load_pct: float = DEFAULT_EXIT_LOAD_PCT,
) -> ExitLoadResult:
    """Compute exit load for a withdrawal.

    Waived if the account is older than EXIT_LOAD_WAIVER_DAYS.
    """
    account = db.get(PortfolioAccountModel, portfolio_account_id)
    if account is None:
        return ExitLoadResult(
            portfolio_account_id=portfolio_account_id,
            withdrawal_paise=withdrawal_paise,
            exit_load_paise=0,
            net_withdrawal_paise=withdrawal_paise,
        )

    days_since_inception = (dt.date.today() - account.inception_date).days

    if days_since_inception >= EXIT_LOAD_WAIVER_DAYS:
        # No exit load after waiver period
        load = 0
    else:
        load = int(withdrawal_paise * exit_load_pct / 100.0)

    return ExitLoadResult(
        portfolio_account_id=portfolio_account_id,
        withdrawal_paise=withdrawal_paise,
        exit_load_paise=load,
        net_withdrawal_paise=withdrawal_paise - load,
    )


def charge_exit_load(
    db: Session,
    portfolio_account_id: uuid.UUID,
    withdrawal_paise: int,
    as_of: dt.date | None = None,
    exit_load_pct: float = DEFAULT_EXIT_LOAD_PCT,
) -> ExitLoadResult:
    """Compute and debit exit load from the account."""
    if as_of is None:
        as_of = dt.date.today()

    result = compute_exit_load(db, portfolio_account_id, withdrawal_paise, exit_load_pct)

    if result.exit_load_paise > 0:
        account = db.get(PortfolioAccountModel, portfolio_account_id)
        if account:
            _debit_fee(
                db, account, result.exit_load_paise, as_of,
                "exit_load", f"Exit load on withdrawal of ₹{withdrawal_paise / 100:.2f}",
            )

    return result


# ── Batch fee run ────────────────────────────────────────────────────────────

def run_quarterly_fees(db: Session, as_of: dt.date | None = None) -> list[FeeChargeResult]:
    """Run management fee billing for all active accounts (quarterly)."""
    if as_of is None:
        as_of = dt.date.today()

    accounts = db.scalars(
        select(PortfolioAccountModel).where(
            PortfolioAccountModel.status == "active",
            PortfolioAccountModel.fee_schedule_id.isnot(None),
        )
    ).all()

    results: list[FeeChargeResult] = []
    for account in accounts:
        try:
            result = charge_management_fee(db, account.id, as_of, days=90)
            if result and result.total_fee_paise > 0:
                results.append(result)
        except Exception as exc:
            logger.error("Mgmt fee failed for %s: %s", account.account_code, exc)

    db.flush()
    logger.info("Quarterly fee run: %d accounts charged for %s", len(results), as_of)
    return results


def run_annual_perf_fees(db: Session, as_of: dt.date | None = None) -> list[FeeChargeResult]:
    """Run performance fee billing for all active accounts (annual)."""
    if as_of is None:
        as_of = dt.date.today()

    accounts = db.scalars(
        select(PortfolioAccountModel).where(
            PortfolioAccountModel.status == "active",
            PortfolioAccountModel.fee_schedule_id.isnot(None),
        )
    ).all()

    results: list[FeeChargeResult] = []
    for account in accounts:
        try:
            result = charge_performance_fee(db, account.id, as_of)
            if result and result.total_fee_paise > 0:
                results.append(result)
        except Exception as exc:
            logger.error("Perf fee failed for %s: %s", account.account_code, exc)

    db.flush()
    logger.info("Annual perf fee run: %d accounts charged for %s", len(results), as_of)
    return results


# ── Internal ─────────────────────────────────────────────────────────────────

def _debit_fee(
    db: Session,
    account: PortfolioAccountModel,
    fee_paise: int,
    posted_on: dt.date,
    entry_type: str,
    description: str,
) -> None:
    """Create a cash ledger debit and reduce account cash balance."""
    account.cash_balance_paise -= fee_paise
    new_balance = account.cash_balance_paise

    db.add(CashLedgerModel(
        portfolio_account_id=account.id,
        entry_type=entry_type,
        amount_paise=-fee_paise,
        balance_paise=new_balance,
        posted_on=posted_on,
        description=description,
    ))
    db.flush()
