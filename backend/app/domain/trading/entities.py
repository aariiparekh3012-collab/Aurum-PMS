"""Trading domain entities — Order and Trade aggregates.

An Order is placed by the RM/PM for a strategy or specific client. Once approved
by compliance, it gets allocated across client portfolios and executed as Trades.

Order lifecycle: DRAFT → PENDING_APPROVAL → APPROVED → ALLOCATED → PARTIALLY_FILLED → FILLED → SETTLED
                                           → REJECTED
                                                                                       → CANCELLED
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum

from app.core.exceptions import InvalidStateTransition


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ALLOCATED = "allocated"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    SETTLED = "settled"


class TradeStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    SETTLED = "settled"
    FAILED = "failed"


@dataclass
class Order:
    """A model-portfolio or single-client order."""

    security_id: uuid.UUID
    strategy_id: uuid.UUID | None
    side: OrderSide
    order_type: OrderType
    quantity: int
    limit_price: Decimal | None = None
    client_id: uuid.UUID | None = None  # if single-client order
    broker_id: uuid.UUID | None = None
    status: OrderStatus = OrderStatus.DRAFT
    placed_by: str = ""
    notes: str = ""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ── state transitions ──
    def submit(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidStateTransition(f"Cannot submit order in {self.status.value}")
        self.status = OrderStatus.PENDING_APPROVAL

    def approve(self) -> None:
        if self.status != OrderStatus.PENDING_APPROVAL:
            raise InvalidStateTransition(f"Cannot approve order in {self.status.value}")
        self.status = OrderStatus.APPROVED

    def reject(self, reason: str = "") -> None:
        if self.status != OrderStatus.PENDING_APPROVAL:
            raise InvalidStateTransition(f"Cannot reject order in {self.status.value}")
        self.status = OrderStatus.REJECTED
        self.notes = reason

    def mark_allocated(self) -> None:
        if self.status != OrderStatus.APPROVED:
            raise InvalidStateTransition(f"Cannot allocate order in {self.status.value}")
        self.status = OrderStatus.ALLOCATED

    def mark_filled(self) -> None:
        if self.status not in (OrderStatus.ALLOCATED, OrderStatus.PARTIALLY_FILLED):
            raise InvalidStateTransition(f"Cannot fill order in {self.status.value}")
        self.status = OrderStatus.FILLED

    def cancel(self) -> None:
        if self.status not in (
            OrderStatus.DRAFT,
            OrderStatus.PENDING_APPROVAL,
            OrderStatus.APPROVED,
        ):
            raise InvalidStateTransition(f"Cannot cancel order in {self.status.value}")
        self.status = OrderStatus.CANCELLED


@dataclass
class OrderAllocation:
    """Splits an approved order across client portfolios."""

    order_id: uuid.UUID
    client_id: uuid.UUID
    portfolio_account_id: uuid.UUID
    quantity: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class Trade:
    """An executed fill against a broker."""

    order_id: uuid.UUID
    allocation_id: uuid.UUID | None
    security_id: uuid.UUID
    client_id: uuid.UUID
    portfolio_account_id: uuid.UUID
    side: OrderSide
    quantity: int
    price: Decimal
    trade_date: date = field(default_factory=date.today)
    settlement_date: date | None = None
    broker_id: uuid.UUID | None = None
    status: TradeStatus = TradeStatus.EXECUTED
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
