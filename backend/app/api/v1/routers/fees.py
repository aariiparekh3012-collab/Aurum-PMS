"""Fee management endpoints — charge fees, preview exit loads, run batch billing."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.services.fee_engine import (
    charge_exit_load,
    charge_management_fee,
    charge_performance_fee,
    compute_exit_load,
    run_annual_perf_fees,
    run_quarterly_fees,
)

router = APIRouter(prefix="/fees", tags=["fees"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class FeeChargeOut(BaseModel):
    portfolio_account_id: uuid.UUID
    account_code: str
    mgmt_fee_paise: int
    perf_fee_paise: int
    total_fee_paise: int
    total_fee_inr: float
    new_cash_balance_paise: int


class ExitLoadPreview(BaseModel):
    portfolio_account_id: uuid.UUID
    withdrawal_paise: int
    withdrawal_inr: float
    exit_load_paise: int
    exit_load_inr: float
    net_withdrawal_paise: int
    net_withdrawal_inr: float


class ExitLoadRequest(BaseModel):
    withdrawal_inr: float = Field(gt=0)
    exit_load_pct: float = Field(ge=0, default=1.0)


class BatchFeeResult(BaseModel):
    as_of: date
    accounts_charged: int
    total_fees_paise: int
    total_fees_inr: float
    details: list[FeeChargeOut]


# ── Single-account endpoints ──────────────────────────────────────────────────

@router.post("/accounts/{account_id}/management-fee", response_model=FeeChargeOut)
def charge_mgmt_fee(
    account_id: uuid.UUID,
    days: int = Query(90, ge=1, le=365, description="Accrual period in days"),
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Charge management fee for a single portfolio account."""
    result = charge_management_fee(db, account_id, as_of, days)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Account not found or no valuation data")
    return FeeChargeOut(
        **result.__dict__,
        total_fee_inr=result.total_fee_paise / 100,
    )


@router.post("/accounts/{account_id}/performance-fee", response_model=FeeChargeOut)
def charge_perf_fee(
    account_id: uuid.UUID,
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Charge performance fee (with HWM) for a single portfolio account."""
    result = charge_performance_fee(db, account_id, as_of)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Account not found or insufficient data")
    return FeeChargeOut(
        **result.__dict__,
        total_fee_inr=result.total_fee_paise / 100,
    )


@router.post("/accounts/{account_id}/exit-load/preview", response_model=ExitLoadPreview)
def preview_exit_load(
    account_id: uuid.UUID,
    body: ExitLoadRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Preview exit load for a proposed withdrawal (does NOT charge)."""
    withdrawal_paise = int(body.withdrawal_inr * 100)
    result = compute_exit_load(db, account_id, withdrawal_paise, body.exit_load_pct)
    return ExitLoadPreview(
        portfolio_account_id=result.portfolio_account_id,
        withdrawal_paise=result.withdrawal_paise,
        withdrawal_inr=result.withdrawal_paise / 100,
        exit_load_paise=result.exit_load_paise,
        exit_load_inr=result.exit_load_paise / 100,
        net_withdrawal_paise=result.net_withdrawal_paise,
        net_withdrawal_inr=result.net_withdrawal_paise / 100,
    )


@router.post("/accounts/{account_id}/exit-load/charge", response_model=ExitLoadPreview)
def charge_exit(
    account_id: uuid.UUID,
    body: ExitLoadRequest,
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Charge exit load for a withdrawal."""
    withdrawal_paise = int(body.withdrawal_inr * 100)
    result = charge_exit_load(db, account_id, withdrawal_paise, as_of, body.exit_load_pct)
    return ExitLoadPreview(
        portfolio_account_id=result.portfolio_account_id,
        withdrawal_paise=result.withdrawal_paise,
        withdrawal_inr=result.withdrawal_paise / 100,
        exit_load_paise=result.exit_load_paise,
        exit_load_inr=result.exit_load_paise / 100,
        net_withdrawal_paise=result.net_withdrawal_paise,
        net_withdrawal_inr=result.net_withdrawal_paise / 100,
    )


# ── Batch endpoints ──────────────────────────────────────────────────────────

@router.post("/batch/quarterly", response_model=BatchFeeResult)
def batch_quarterly_fees(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Run quarterly management fee billing for all active accounts."""
    target = as_of or date.today()
    results = run_quarterly_fees(db, target)
    total = sum(r.total_fee_paise for r in results)
    return BatchFeeResult(
        as_of=target,
        accounts_charged=len(results),
        total_fees_paise=total,
        total_fees_inr=total / 100,
        details=[
            FeeChargeOut(**r.__dict__, total_fee_inr=r.total_fee_paise / 100)
            for r in results
        ],
    )


@router.post("/batch/annual-performance", response_model=BatchFeeResult)
def batch_annual_perf_fees(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Run annual performance fee billing for all active accounts."""
    target = as_of or date.today()
    results = run_annual_perf_fees(db, target)
    total = sum(r.total_fee_paise for r in results)
    return BatchFeeResult(
        as_of=target,
        accounts_charged=len(results),
        total_fees_paise=total,
        total_fees_inr=total / 100,
        details=[
            FeeChargeOut(**r.__dict__, total_fee_inr=r.total_fee_paise / 100)
            for r in results
        ],
    )
