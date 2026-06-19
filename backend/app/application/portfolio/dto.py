"""Portfolio application DTOs."""
from __future__ import annotations
import uuid
import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class ProvisionClientCommand:
    onboarding_application_id: uuid.UUID

@dataclass(frozen=True)
class CreatePortfolioCommand:
    client_id: uuid.UUID
    strategy_id: uuid.UUID
    fee_schedule_id: uuid.UUID | None = None

@dataclass(frozen=True)
class RecordTradeCommand:
    portfolio_account_id: uuid.UUID
    security_id: uuid.UUID
    side: str   # buy | sell
    quantity: float
    price_inr: float

@dataclass(frozen=True)
class CapitalFlowCommand:
    portfolio_account_id: uuid.UUID
    flow_type: str  # contribution | withdrawal
    amount_inr: float

# ── Read models ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClientView:
    id: uuid.UUID
    client_code: str
    full_name: str
    email: str
    investor_type: str
    status: str

@dataclass(frozen=True)
class HoldingView:
    security_id: uuid.UUID
    security_name: str
    isin: str
    quantity: float
    avg_cost_inr: float
    current_price_inr: float | None
    market_value_inr: float | None
    pnl_inr: float | None
    weight_pct: float | None

@dataclass(frozen=True)
class PortfolioView:
    id: uuid.UUID
    account_code: str
    strategy_name: str
    status: str
    inception_date: str
    cash_balance_inr: float
    invested_value_inr: float
    holdings_count: int

@dataclass(frozen=True)
class TradeView:
    id: uuid.UUID
    side: str
    security_name: str
    quantity: float
    price_inr: float
    value_inr: float
    traded_at: str

@dataclass(frozen=True)
class CashLedgerView:
    entry_type: str
    amount_inr: float
    posted_on: str
    description: str
