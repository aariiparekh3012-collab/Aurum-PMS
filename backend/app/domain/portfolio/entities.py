"""Portfolio domain entities — Client, PortfolioAccount, Holding, Order, Trade."""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field

from app.core.exceptions import InvalidStateTransition, ValidationError
from app.domain.portfolio import events
from app.domain.portfolio.enums import (
    AssetKind, CashEntryType, ClientStatus, FlowType,
    OrderSide, OrderStatus, PortfolioStatus,
)
from app.domain.portfolio.value_objects import Price, Quantity


# ── Client (provisioned from onboarding) ─────────────────────────────────

@dataclass
class Client:
    """Golden record — created when onboarding reaches ACTIVE."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    onboarding_application_id: uuid.UUID | None = None
    client_code: str = ""
    pan_hash: str = ""
    investor_type: str = ""
    full_name: str = ""
    email: str = ""
    status: ClientStatus = ClientStatus.ACTIVE
    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    _events: list = field(default_factory=list, repr=False, init=False)

    def pull_events(self):
        out, self._events = self._events, []
        return out

    @classmethod
    def provision(
        cls, *, onboarding_application_id: uuid.UUID, client_code: str,
        pan_hash: str, investor_type: str, full_name: str, email: str,
    ) -> "Client":
        c = cls(
            onboarding_application_id=onboarding_application_id,
            client_code=client_code, pan_hash=pan_hash,
            investor_type=investor_type, full_name=full_name, email=email,
        )
        c._events.append(events.ClientProvisioned(aggregate_id=c.id, client_code=client_code))
        return c


# ── Holding + Tax Lot ────────────────────────────────────────────────────

@dataclass
class HoldingLot:
    """FIFO tax lot for a specific acquisition."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    quantity: float = 0
    cost_paise: int = 0
    acquired_on: dt.date = field(default_factory=dt.date.today)


@dataclass
class Holding:
    """Aggregated position in a single security within a portfolio."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    portfolio_account_id: uuid.UUID = field(default_factory=uuid.uuid4)
    security_id: uuid.UUID = field(default_factory=uuid.uuid4)
    quantity: float = 0
    avg_cost_paise: int = 0
    lots: list[HoldingLot] = field(default_factory=list)

    @property
    def market_value_paise(self) -> int:
        """Needs current price — computed externally."""
        return 0  # placeholder; valuation service fills this

    @property
    def total_cost_paise(self) -> int:
        return round(self.quantity * self.avg_cost_paise)

    def add_lot(self, qty: float, price_paise: int, date: dt.date | None = None) -> None:
        """Add shares from a buy trade."""
        if qty <= 0:
            raise ValidationError("Lot quantity must be positive", code="invalid_lot")
        lot = HoldingLot(quantity=qty, cost_paise=price_paise, acquired_on=date or dt.date.today())
        self.lots.append(lot)
        # recalculate average cost
        total_cost = sum(l.quantity * l.cost_paise for l in self.lots)
        total_qty = sum(l.quantity for l in self.lots)
        self.quantity = total_qty
        self.avg_cost_paise = round(total_cost / total_qty) if total_qty else 0

    def remove_fifo(self, qty: float) -> list[HoldingLot]:
        """Remove shares using FIFO. Returns consumed lots for tax calculation."""
        if qty > self.quantity + 0.0001:
            raise ValidationError(
                f"Cannot sell {qty} — only {self.quantity} held", code="insufficient_holding"
            )
        remaining = qty
        consumed = []
        new_lots = []
        for lot in self.lots:
            if remaining <= 0:
                new_lots.append(lot)
                continue
            if lot.quantity <= remaining:
                consumed.append(lot)
                remaining -= lot.quantity
            else:
                consumed.append(HoldingLot(
                    quantity=remaining, cost_paise=lot.cost_paise, acquired_on=lot.acquired_on,
                ))
                new_lots.append(HoldingLot(
                    id=lot.id, quantity=lot.quantity - remaining,
                    cost_paise=lot.cost_paise, acquired_on=lot.acquired_on,
                ))
                remaining = 0
        self.lots = new_lots
        total_qty = sum(l.quantity for l in self.lots)
        total_cost = sum(l.quantity * l.cost_paise for l in self.lots)
        self.quantity = total_qty
        self.avg_cost_paise = round(total_cost / total_qty) if total_qty else 0
        return consumed


# ── Capital Flow ─────────────────────────────────────────────────────────

@dataclass
class CapitalFlow:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    portfolio_account_id: uuid.UUID = field(default_factory=uuid.uuid4)
    flow_type: FlowType = FlowType.CONTRIBUTION
    asset_kind: AssetKind = AssetKind.CASH
    amount_paise: int = 0
    value_date: dt.date = field(default_factory=dt.date.today)


# ── Cash Ledger Entry ────────────────────────────────────────────────────

@dataclass
class CashLedgerEntry:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    portfolio_account_id: uuid.UUID = field(default_factory=uuid.uuid4)
    entry_type: CashEntryType = CashEntryType.CONTRIBUTION
    amount_paise: int = 0
    posted_on: dt.date = field(default_factory=dt.date.today)
    description: str = ""


# ── Trade ────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    order_id: uuid.UUID | None = None
    portfolio_account_id: uuid.UUID = field(default_factory=uuid.uuid4)
    security_id: uuid.UUID = field(default_factory=uuid.uuid4)
    broker_id: uuid.UUID | None = None
    side: OrderSide = OrderSide.BUY
    quantity: float = 0
    price_paise: int = 0
    traded_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    @property
    def value_paise(self) -> int:
        return round(self.quantity * self.price_paise)


# ── Order ────────────────────────────────────────────────────────────────

@dataclass
class Order:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    strategy_id: uuid.UUID = field(default_factory=uuid.uuid4)
    security_id: uuid.UUID = field(default_factory=uuid.uuid4)
    side: OrderSide = OrderSide.BUY
    quantity: float = 0
    filled_quantity: float = 0
    status: OrderStatus = OrderStatus.DRAFT
    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    _events: list = field(default_factory=list, repr=False, init=False)

    def pull_events(self):
        out, self._events = self._events, []
        return out

    def submit(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidStateTransition(f"Cannot submit order in {self.status.value}")
        self.status = OrderStatus.PENDING

    def fill(
        self,
        qty: float,
        price_paise: int,
        *,
        portfolio_account_id: uuid.UUID | None = None,
    ) -> Trade:
        if self.status not in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED):
            raise InvalidStateTransition(f"Cannot fill order in {self.status.value}")
        if qty > (self.quantity - self.filled_quantity + 0.0001):
            raise ValidationError("Fill exceeds remaining order quantity", code="overfill")
        self.filled_quantity += qty
        if abs(self.filled_quantity - self.quantity) < 0.0001:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
        trade = Trade(
            order_id=self.id,
            security_id=self.security_id,
            side=self.side,
            quantity=qty,
            price_paise=price_paise,
            portfolio_account_id=portfolio_account_id or uuid.uuid4(),
        )
        return trade

    def cancel(self) -> None:
        if self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            raise InvalidStateTransition(f"Cannot cancel order in {self.status.value}")
        self.status = OrderStatus.CANCELLED


# ── Portfolio Account ────────────────────────────────────────────────────

@dataclass
class PortfolioAccount:
    """A single managed portfolio for a client under a strategy."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    client_id: uuid.UUID = field(default_factory=uuid.uuid4)
    strategy_id: uuid.UUID = field(default_factory=uuid.uuid4)
    demat_account_id: uuid.UUID | None = None
    fee_schedule_id: uuid.UUID | None = None
    account_code: str = ""
    status: PortfolioStatus = PortfolioStatus.PENDING
    inception_date: dt.date = field(default_factory=dt.date.today)
    cash_balance_paise: int = 0

    holdings: dict[uuid.UUID, Holding] = field(default_factory=dict)  # security_id -> Holding
    cash_ledger: list[CashLedgerEntry] = field(default_factory=list)
    capital_flows: list[CapitalFlow] = field(default_factory=list)

    _events: list = field(default_factory=list, repr=False, init=False)

    def pull_events(self):
        out, self._events = self._events, []
        return out

    def activate(self) -> None:
        if self.status != PortfolioStatus.PENDING:
            raise InvalidStateTransition("Can only activate a pending portfolio")
        self.status = PortfolioStatus.ACTIVE

    def contribute(self, amount_paise: int, value_date: dt.date | None = None) -> CapitalFlow:
        if amount_paise <= 0:
            raise ValidationError("Contribution must be positive", code="invalid_flow")
        vd = value_date or dt.date.today()
        flow = CapitalFlow(
            portfolio_account_id=self.id, flow_type=FlowType.CONTRIBUTION,
            amount_paise=amount_paise, value_date=vd,
        )
        self.capital_flows.append(flow)
        self.cash_balance_paise += amount_paise
        self.cash_ledger.append(CashLedgerEntry(
            portfolio_account_id=self.id, entry_type=CashEntryType.CONTRIBUTION,
            amount_paise=amount_paise, posted_on=vd, description="Capital contribution",
        ))
        if self.status == PortfolioStatus.PENDING:
            self.activate()
        self._events.append(events.CapitalFlowRecorded(
            aggregate_id=self.id, flow_type="contribution", amount_paise=amount_paise,
        ))
        return flow

    def withdraw(self, amount_paise: int, value_date: dt.date | None = None) -> CapitalFlow:
        if amount_paise <= 0:
            raise ValidationError("Withdrawal must be positive", code="invalid_flow")
        if amount_paise > self.cash_balance_paise:
            raise ValidationError("Insufficient cash balance", code="insufficient_cash")
        vd = value_date or dt.date.today()
        flow = CapitalFlow(
            portfolio_account_id=self.id, flow_type=FlowType.WITHDRAWAL,
            amount_paise=amount_paise, value_date=vd,
        )
        self.capital_flows.append(flow)
        self.cash_balance_paise -= amount_paise
        self.cash_ledger.append(CashLedgerEntry(
            portfolio_account_id=self.id, entry_type=CashEntryType.WITHDRAWAL,
            amount_paise=-amount_paise, posted_on=vd, description="Capital withdrawal",
        ))
        self._events.append(events.CapitalFlowRecorded(
            aggregate_id=self.id, flow_type="withdrawal", amount_paise=amount_paise,
        ))
        return flow

    def record_buy(self, security_id: uuid.UUID, qty: float, price_paise: int) -> Trade:
        cost = round(qty * price_paise)
        if cost > self.cash_balance_paise:
            raise ValidationError("Insufficient cash for buy", code="insufficient_cash")
        trade = Trade(
            portfolio_account_id=self.id, security_id=security_id,
            side=OrderSide.BUY, quantity=qty, price_paise=price_paise,
        )
        # update holding
        if security_id not in self.holdings:
            self.holdings[security_id] = Holding(
                portfolio_account_id=self.id, security_id=security_id,
            )
        self.holdings[security_id].add_lot(qty, price_paise)
        # debit cash
        self.cash_balance_paise -= cost
        self.cash_ledger.append(CashLedgerEntry(
            portfolio_account_id=self.id, entry_type=CashEntryType.BUY_DEBIT,
            amount_paise=-cost, posted_on=dt.date.today(),
            description=f"Buy {qty} @ {price_paise/100:.2f}",
        ))
        self._events.append(events.TradeExecuted(
            aggregate_id=self.id, side="buy",
            quantity=qty, price_paise=price_paise,
        ))
        return trade

    def record_sell(self, security_id: uuid.UUID, qty: float, price_paise: int) -> tuple[Trade, list[HoldingLot]]:
        if security_id not in self.holdings:
            raise ValidationError("No holding for this security", code="no_holding")
        holding = self.holdings[security_id]
        consumed_lots = holding.remove_fifo(qty)
        proceeds = round(qty * price_paise)
        trade = Trade(
            portfolio_account_id=self.id, security_id=security_id,
            side=OrderSide.SELL, quantity=qty, price_paise=price_paise,
        )
        self.cash_balance_paise += proceeds
        self.cash_ledger.append(CashLedgerEntry(
            portfolio_account_id=self.id, entry_type=CashEntryType.SELL_CREDIT,
            amount_paise=proceeds, posted_on=dt.date.today(),
            description=f"Sell {qty} @ {price_paise/100:.2f}",
        ))
        if holding.quantity == 0:
            del self.holdings[security_id]
        self._events.append(events.TradeExecuted(
            aggregate_id=self.id, side="sell",
            quantity=qty, price_paise=price_paise,
        ))
        return trade, consumed_lots

    @property
    def total_cost_paise(self) -> int:
        return sum(h.total_cost_paise for h in self.holdings.values())
