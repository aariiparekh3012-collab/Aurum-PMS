"""Portfolio domain enumerations."""
from __future__ import annotations
from enum import Enum


class PortfolioStatus(str, Enum):
    PENDING = "pending"          # provisioned, awaiting first contribution
    ACTIVE = "active"            # funded and actively managed
    SUSPENDED = "suspended"      # temporarily suspended (compliance hold)
    CLOSED = "closed"            # terminated, all positions liquidated


class ClientStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    CLOSED = "closed"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"          # approved, awaiting execution
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"


class FlowType(str, Enum):
    CONTRIBUTION = "contribution"
    WITHDRAWAL = "withdrawal"


class AssetKind(str, Enum):
    CASH = "cash"
    SECURITIES = "securities"


class CashEntryType(str, Enum):
    CONTRIBUTION = "contribution"
    WITHDRAWAL = "withdrawal"
    BUY_DEBIT = "buy_debit"
    SELL_CREDIT = "sell_credit"
    DIVIDEND = "dividend"
    FEE_DEBIT = "fee_debit"
    INTEREST = "interest"


class InstrumentType(str, Enum):
    EQUITY = "equity"
    DEBT = "debt"
    MUTUAL_FUND = "mutual_fund"
    ETF = "etf"
    REIT = "reit"
