"""Dashboard stats endpoint — single call for frontend KPIs and charts."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models import OnboardingApplicationModel
from app.infrastructure.db.models_client import ClientModel, ClientRiskProfileModel
from app.infrastructure.db.models_portfolio import PortfolioAccountModel
from app.infrastructure.db.models_performance import ValuationSnapshotModel
from app.infrastructure.db.models_trading import OrderModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class StatusCount(BaseModel):
    status: str
    count: int


class RiskCount(BaseModel):
    category: str
    count: int


class DashboardResponse(BaseModel):
    total_clients: int
    active_clients: int
    total_applications: int
    pending_review: int
    total_aum_paise: int
    total_portfolio_accounts: int
    pending_orders: int
    applications_by_status: list[StatusCount]
    clients_by_risk: list[RiskCount]


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.get_current_user),
):
    # Client counts
    total_clients = db.scalar(select(func.count()).select_from(ClientModel)) or 0
    active_clients = db.scalar(
        select(func.count()).select_from(ClientModel).where(ClientModel.status == "active")
    ) or 0

    # Application counts
    total_apps = db.scalar(
        select(func.count()).select_from(OnboardingApplicationModel)
    ) or 0
    pending_review = db.scalar(
        select(func.count())
        .select_from(OnboardingApplicationModel)
        .where(OnboardingApplicationModel.status == "under_review")
    ) or 0

    # Portfolio & AUM — sum of latest valuation snapshot per account
    # Subquery: max snapshot date per account
    latest_snap_subq = (
        select(
            ValuationSnapshotModel.portfolio_account_id,
            func.max(ValuationSnapshotModel.as_of).label("latest_date"),
        )
        .group_by(ValuationSnapshotModel.portfolio_account_id)
        .subquery()
    )
    aum_rows = db.execute(
        select(func.sum(ValuationSnapshotModel.market_value_paise))
        .join(
            latest_snap_subq,
            (ValuationSnapshotModel.portfolio_account_id == latest_snap_subq.c.portfolio_account_id)
            & (ValuationSnapshotModel.as_of == latest_snap_subq.c.latest_date),
        )
    ).scalar()
    total_aum_paise = int(aum_rows or 0)

    total_portfolio_accounts = db.scalar(
        select(func.count()).select_from(PortfolioAccountModel)
    ) or 0

    # Pending orders awaiting approval
    pending_orders = db.scalar(
        select(func.count())
        .select_from(OrderModel)
        .where(OrderModel.status == "pending_approval")
    ) or 0

    # Applications grouped by status
    status_rows = db.execute(
        select(
            OnboardingApplicationModel.status,
            func.count().label("cnt"),
        ).group_by(OnboardingApplicationModel.status)
    ).all()
    by_status = [StatusCount(status=r[0], count=r[1]) for r in status_rows]

    # Clients grouped by risk category
    risk_rows = db.execute(
        select(
            ClientRiskProfileModel.category,
            func.count().label("cnt"),
        ).group_by(ClientRiskProfileModel.category)
    ).all()
    by_risk = [RiskCount(category=r[0], count=r[1]) for r in risk_rows]

    return DashboardResponse(
        total_clients=total_clients,
        active_clients=active_clients,
        total_applications=total_apps,
        pending_review=pending_review,
        total_aum_paise=total_aum_paise,
        total_portfolio_accounts=total_portfolio_accounts,
        pending_orders=pending_orders,
        applications_by_status=by_status,
        clients_by_risk=by_risk,
    )
