"""Dashboard stats endpoint — single call for frontend KPIs and charts."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.core.security import decrypt_pii
from app.infrastructure.db.models_onboarding import OnboardingApplicationModel
from app.infrastructure.db.models_client import ClientModel, ClientRiskProfileModel
from app.infrastructure.db.models_portfolio import (
    CashLedgerModel,
    FeeScheduleModel,
    HoldingModel,
    PortfolioAccountModel,
)
from app.infrastructure.db.models_performance import (
    PerformanceReturnModel,
    ValuationSnapshotModel,
)
from app.infrastructure.db.models_reference import StrategyModel
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


# ── RM Dashboard ──────────────────────────────────────────────────────────────


class ClientRow(BaseModel):
    client_id: uuid.UUID
    client_code: str
    full_name: str
    status: str
    investor_type: str
    risk_category: str | None = None
    portfolio_count: int = 0
    total_aum_paise: int = 0
    total_cost_paise: int = 0
    unrealised_pnl_paise: int = 0
    cash_paise: int = 0
    inception_date: str | None = None


class StrategyBreakdown(BaseModel):
    strategy_name: str
    account_count: int
    total_aum_paise: int


class RecentActivity(BaseModel):
    kind: str
    description: str
    date: str


class RMDashboardResponse(BaseModel):
    total_clients: int
    active_clients: int
    total_aum_paise: int
    total_portfolios: int
    pending_orders: int
    pending_review: int
    clients: list[ClientRow]
    strategy_breakdown: list[StrategyBreakdown]
    recent_activity: list[RecentActivity]


@router.get("/rm", response_model=RMDashboardResponse)
def get_rm_dashboard(
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """RM dashboard — client book with AUM, strategy breakdown, recent activity."""
    clients_orm = db.scalars(
        select(ClientModel).order_by(ClientModel.full_name)
    ).all()

    # Build AUM map from latest snapshots
    latest_snap_subq = (
        select(
            ValuationSnapshotModel.portfolio_account_id,
            func.max(ValuationSnapshotModel.as_of).label("latest_date"),
        )
        .group_by(ValuationSnapshotModel.portfolio_account_id)
        .subquery()
    )
    snap_rows = db.execute(
        select(
            ValuationSnapshotModel.portfolio_account_id,
            ValuationSnapshotModel.market_value_paise,
        )
        .join(
            latest_snap_subq,
            (ValuationSnapshotModel.portfolio_account_id == latest_snap_subq.c.portfolio_account_id)
            & (ValuationSnapshotModel.as_of == latest_snap_subq.c.latest_date),
        )
    ).all()
    aum_by_account = {r[0]: r[1] for r in snap_rows}

    # All portfolio accounts
    all_accounts = db.scalars(select(PortfolioAccountModel)).all()
    accts_by_client: dict[uuid.UUID, list] = {}
    for a in all_accounts:
        accts_by_client.setdefault(a.client_id, []).append(a)

    # Strategy names
    strategies = {s.id: s.name for s in db.scalars(select(StrategyModel)).all()}

    # Build client rows
    client_rows: list[ClientRow] = []
    total_aum = 0
    for c in clients_orm:
        accts = accts_by_client.get(c.id, [])
        client_aum = sum(aum_by_account.get(a.id, 0) for a in accts)
        client_cost = 0
        client_cash = 0
        earliest = None
        for a in accts:
            holdings = db.scalars(
                select(HoldingModel).where(HoldingModel.portfolio_account_id == a.id)
            ).all()
            client_cost += sum(int(h.avg_cost_paise * float(h.quantity)) for h in holdings)
            client_cash += a.cash_balance_paise
            if earliest is None or a.inception_date < earliest:
                earliest = a.inception_date

        total_aum += client_aum

        latest_risk = None
        if hasattr(c, "risk_profiles") and c.risk_profiles:
            latest_risk = max(c.risk_profiles, key=lambda r: r.effective_from).category

        client_rows.append(ClientRow(
            client_id=c.id,
            client_code=c.client_code,
            full_name=c.full_name,
            status=c.status,
            investor_type=c.investor_type,
            risk_category=latest_risk,
            portfolio_count=len(accts),
            total_aum_paise=client_aum,
            total_cost_paise=client_cost,
            unrealised_pnl_paise=client_aum - client_cost,
            cash_paise=client_cash,
            inception_date=earliest.isoformat() if earliest else None,
        ))

    # Strategy breakdown
    strat_map: dict[str, dict] = {}
    for a in all_accounts:
        sname = strategies.get(a.strategy_id, "Unknown")
        if sname not in strat_map:
            strat_map[sname] = {"count": 0, "aum": 0}
        strat_map[sname]["count"] += 1
        strat_map[sname]["aum"] += aum_by_account.get(a.id, 0)
    strategy_breakdown = [
        StrategyBreakdown(strategy_name=k, account_count=v["count"], total_aum_paise=v["aum"])
        for k, v in sorted(strat_map.items(), key=lambda x: -x[1]["aum"])
    ]

    # Recent activity — latest cash ledger entries + recent onboarding
    recent: list[RecentActivity] = []
    recent_cash = db.scalars(
        select(CashLedgerModel).order_by(desc(CashLedgerModel.posted_on)).limit(10)
    ).all()
    for e in recent_cash:
        acct = db.get(PortfolioAccountModel, e.portfolio_account_id)
        code = acct.account_code if acct else "?"
        recent.append(RecentActivity(
            kind=e.entry_type,
            description=f"{code}: {e.entry_type.replace('_', ' ')} — ₹{abs(e.amount_paise)/100:,.0f}",
            date=e.posted_on.isoformat(),
        ))
    recent_apps = db.scalars(
        select(OnboardingApplicationModel)
        .order_by(desc(OnboardingApplicationModel.created_at))
        .limit(5)
    ).all()
    for a in recent_apps:
        recent.append(RecentActivity(
            kind="onboarding",
            description=f"{a.full_name} — {a.status.replace('_', ' ')}",
            date=a.created_at.date().isoformat() if a.created_at else "",
        ))
    recent.sort(key=lambda r: r.date, reverse=True)

    # Counts
    pending_review = db.scalar(
        select(func.count())
        .select_from(OnboardingApplicationModel)
        .where(OnboardingApplicationModel.status == "under_review")
    ) or 0
    pending_orders = db.scalar(
        select(func.count())
        .select_from(OrderModel)
        .where(OrderModel.status == "pending_approval")
    ) or 0

    return RMDashboardResponse(
        total_clients=len(clients_orm),
        active_clients=sum(1 for c in clients_orm if c.status == "active"),
        total_aum_paise=total_aum,
        total_portfolios=len(all_accounts),
        pending_orders=pending_orders,
        pending_review=pending_review,
        clients=client_rows,
        strategy_breakdown=strategy_breakdown,
        recent_activity=recent[:15],
    )


# ── Compliance Dashboard ──────────────────────────────────────────────────────


class OnboardingPipelineItem(BaseModel):
    id: uuid.UUID
    full_name: str
    status: str
    investor_type: str
    proposed_investment_inr: float
    created_at: str
    risk_category: str | None = None


class FeeCollectionSummary(BaseModel):
    total_mgmt_fees_paise: int
    total_perf_fees_paise: int
    total_exit_load_paise: int
    total_fees_paise: int


class ComplianceDashboardResponse(BaseModel):
    total_clients: int
    active_clients: int
    total_aum_paise: int
    total_portfolios: int
    pending_review: int
    pending_orders: int
    onboarding_pipeline: list[OnboardingPipelineItem]
    fee_summary: FeeCollectionSummary
    applications_by_status: list[StatusCount]
    clients_by_risk: list[RiskCount]
    accounts_without_fee_schedule: int


@router.get("/compliance", response_model=ComplianceDashboardResponse)
def get_compliance_dashboard(
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Compliance dashboard — regulatory overview, onboarding pipeline, fee collection."""
    # Core counts
    total_clients = db.scalar(select(func.count()).select_from(ClientModel)) or 0
    active_clients = db.scalar(
        select(func.count()).select_from(ClientModel).where(ClientModel.status == "active")
    ) or 0

    # AUM
    latest_snap_subq = (
        select(
            ValuationSnapshotModel.portfolio_account_id,
            func.max(ValuationSnapshotModel.as_of).label("latest_date"),
        )
        .group_by(ValuationSnapshotModel.portfolio_account_id)
        .subquery()
    )
    aum = db.execute(
        select(func.sum(ValuationSnapshotModel.market_value_paise))
        .join(
            latest_snap_subq,
            (ValuationSnapshotModel.portfolio_account_id == latest_snap_subq.c.portfolio_account_id)
            & (ValuationSnapshotModel.as_of == latest_snap_subq.c.latest_date),
        )
    ).scalar()
    total_aum_paise = int(aum or 0)

    total_portfolios = db.scalar(
        select(func.count()).select_from(PortfolioAccountModel)
    ) or 0

    pending_review = db.scalar(
        select(func.count())
        .select_from(OnboardingApplicationModel)
        .where(OnboardingApplicationModel.status == "under_review")
    ) or 0

    pending_orders = db.scalar(
        select(func.count())
        .select_from(OrderModel)
        .where(OrderModel.status == "pending_approval")
    ) or 0

    # Onboarding pipeline — non-terminal applications
    terminal = {"active", "rejected", "closed"}
    pipeline_apps = db.scalars(
        select(OnboardingApplicationModel)
        .where(OnboardingApplicationModel.status.notin_(terminal))
        .order_by(desc(OnboardingApplicationModel.created_at))
        .limit(25)
    ).all()
    pipeline = [
        OnboardingPipelineItem(
            id=a.id,
            full_name=a.full_name,
            status=a.status,
            investor_type=a.investor_type,
            proposed_investment_inr=float(a.proposed_investment_paise) / 100,
            created_at=a.created_at.isoformat() if a.created_at else "",
            risk_category=a.risk_category,
        )
        for a in pipeline_apps
    ]

    # Fee collection — sum fee-type cash ledger entries
    fee_types = {"mgmt_fee", "perf_fee", "exit_load"}
    fee_entries = db.execute(
        select(
            CashLedgerModel.entry_type,
            func.sum(func.abs(CashLedgerModel.amount_paise)).label("total"),
        )
        .where(CashLedgerModel.entry_type.in_(fee_types))
        .group_by(CashLedgerModel.entry_type)
    ).all()
    fee_map = {r[0]: int(r[1]) for r in fee_entries}
    fee_summary = FeeCollectionSummary(
        total_mgmt_fees_paise=fee_map.get("mgmt_fee", 0),
        total_perf_fees_paise=fee_map.get("perf_fee", 0),
        total_exit_load_paise=fee_map.get("exit_load", 0),
        total_fees_paise=sum(fee_map.values()),
    )

    # Applications by status
    status_rows = db.execute(
        select(
            OnboardingApplicationModel.status,
            func.count().label("cnt"),
        ).group_by(OnboardingApplicationModel.status)
    ).all()
    by_status = [StatusCount(status=r[0], count=r[1]) for r in status_rows]

    # Clients by risk
    risk_rows = db.execute(
        select(
            ClientRiskProfileModel.category,
            func.count().label("cnt"),
        ).group_by(ClientRiskProfileModel.category)
    ).all()
    by_risk = [RiskCount(category=r[0], count=r[1]) for r in risk_rows]

    # Accounts without fee schedule — regulatory flag
    no_fee = db.scalar(
        select(func.count())
        .select_from(PortfolioAccountModel)
        .where(PortfolioAccountModel.fee_schedule_id.is_(None))
        .where(PortfolioAccountModel.status == "active")
    ) or 0

    return ComplianceDashboardResponse(
        total_clients=total_clients,
        active_clients=active_clients,
        total_aum_paise=total_aum_paise,
        total_portfolios=total_portfolios,
        pending_review=pending_review,
        pending_orders=pending_orders,
        onboarding_pipeline=pipeline,
        fee_summary=fee_summary,
        applications_by_status=by_status,
        clients_by_risk=by_risk,
        accounts_without_fee_schedule=no_fee,
    )
