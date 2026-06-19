"""Tests for portfolio domain entities — holdings, FIFO, orders, account."""
from __future__ import annotations

import datetime as dt
import uuid
import pytest

from app.domain.portfolio.entities import (
    Client, Holding, HoldingLot, PortfolioAccount, Order, Trade,
)
from app.domain.portfolio.enums import (
    ClientStatus, OrderSide, OrderStatus, PortfolioStatus,
)
from app.core.exceptions import InvalidStateTransition, ValidationError


# ── Holding + FIFO ──────────────────────────────────────────────────────

class TestHolding:
    def test_add_single_lot(self):
        h = Holding(security_id=uuid.uuid4())
        h.add_lot(100, 15000, dt.date(2024, 1, 10))
        assert h.quantity == 100
        assert h.avg_cost_paise == 15000
        assert len(h.lots) == 1

    def test_add_multiple_lots_recalculates_avg(self):
        h = Holding(security_id=uuid.uuid4())
        h.add_lot(100, 10000)   # 100 @ 100.00
        h.add_lot(100, 20000)   # 100 @ 200.00
        assert h.quantity == 200
        # avg = (100*10000 + 100*20000) / 200 = 15000
        assert h.avg_cost_paise == 15000

    def test_add_lot_zero_qty_raises(self):
        h = Holding(security_id=uuid.uuid4())
        with pytest.raises(ValidationError):
            h.add_lot(0, 15000)

    def test_remove_fifo_partial(self):
        h = Holding(security_id=uuid.uuid4())
        h.add_lot(100, 10000, dt.date(2024, 1, 1))
        h.add_lot(100, 20000, dt.date(2024, 2, 1))
        consumed = h.remove_fifo(50)
        assert len(consumed) == 1
        assert consumed[0].quantity == 50
        assert consumed[0].cost_paise == 10000  # first lot
        assert h.quantity == 150
        # remaining: 50@10000 + 100@20000 = 2_500_000 / 150 ≈ 16667
        assert h.avg_cost_paise == round((50 * 10000 + 100 * 20000) / 150)

    def test_remove_fifo_spans_lots(self):
        h = Holding(security_id=uuid.uuid4())
        h.add_lot(50, 10000, dt.date(2024, 1, 1))
        h.add_lot(100, 20000, dt.date(2024, 2, 1))
        consumed = h.remove_fifo(80)
        # should consume all 50 of lot1 + 30 of lot2
        assert len(consumed) == 2
        assert consumed[0].quantity == 50
        assert consumed[1].quantity == 30
        assert h.quantity == 70
        assert len(h.lots) == 1

    def test_remove_fifo_all(self):
        h = Holding(security_id=uuid.uuid4())
        h.add_lot(100, 10000)
        consumed = h.remove_fifo(100)
        assert h.quantity == 0
        assert h.avg_cost_paise == 0
        assert len(h.lots) == 0

    def test_remove_fifo_insufficient(self):
        h = Holding(security_id=uuid.uuid4())
        h.add_lot(50, 10000)
        with pytest.raises(ValidationError, match="Cannot sell"):
            h.remove_fifo(100)


# ── Order state machine ────────────────────────────────────────────────

class TestOrder:
    def _make(self, qty=100) -> Order:
        return Order(
            strategy_id=uuid.uuid4(), security_id=uuid.uuid4(),
            side=OrderSide.BUY, quantity=qty,
        )

    def test_submit(self):
        o = self._make()
        o.submit()
        assert o.status == OrderStatus.PENDING

    def test_fill_full(self):
        o = self._make(100)
        o.submit()
        trade = o.fill(100, 15000)
        assert o.status == OrderStatus.FILLED
        assert trade.quantity == 100

    def test_fill_partial(self):
        o = self._make(100)
        o.submit()
        o.fill(40, 15000)
        assert o.status == OrderStatus.PARTIALLY_FILLED
        o.fill(60, 15100)
        assert o.status == OrderStatus.FILLED

    def test_fill_overfill_raises(self):
        o = self._make(100)
        o.submit()
        with pytest.raises(ValidationError, match="Fill exceeds"):
            o.fill(200, 15000)

    def test_cancel_pending(self):
        o = self._make()
        o.submit()
        o.cancel()
        assert o.status == OrderStatus.CANCELLED

    def test_cancel_filled_raises(self):
        o = self._make(10)
        o.submit()
        o.fill(10, 100)
        with pytest.raises(InvalidStateTransition):
            o.cancel()

    def test_submit_non_draft_raises(self):
        o = self._make()
        o.submit()
        with pytest.raises(InvalidStateTransition):
            o.submit()


# ── PortfolioAccount ───────────────────────────────────────────────────

class TestPortfolioAccount:
    def _make(self) -> PortfolioAccount:
        return PortfolioAccount(
            client_id=uuid.uuid4(), strategy_id=uuid.uuid4(),
            account_code="PA-TEST", inception_date=dt.date(2024, 1, 1),
        )

    def test_contribute_activates(self):
        a = self._make()
        assert a.status == PortfolioStatus.PENDING
        flow = a.contribute(5_000_000_00)
        assert a.status == PortfolioStatus.ACTIVE
        assert a.cash_balance_paise == 5_000_000_00
        assert flow.flow_type.value == "contribution"

    def test_withdraw(self):
        a = self._make()
        a.contribute(10_000_000_00)
        a.withdraw(3_000_000_00)
        assert a.cash_balance_paise == 7_000_000_00

    def test_withdraw_insufficient(self):
        a = self._make()
        a.contribute(1_000_00)
        with pytest.raises(ValidationError, match="Insufficient cash"):
            a.withdraw(2_000_00)

    def test_buy_creates_holding(self):
        a = self._make()
        a.contribute(10_000_000_00)
        sec = uuid.uuid4()
        trade = a.record_buy(sec, 100, 15000)
        assert sec in a.holdings
        assert a.holdings[sec].quantity == 100
        assert a.cash_balance_paise == 10_000_000_00 - (100 * 15000)
        assert trade.side == OrderSide.BUY

    def test_buy_insufficient_cash(self):
        a = self._make()
        a.contribute(100_00)
        with pytest.raises(ValidationError, match="Insufficient cash"):
            a.record_buy(uuid.uuid4(), 100, 15000)

    def test_sell(self):
        a = self._make()
        a.contribute(10_000_000_00)
        sec = uuid.uuid4()
        a.record_buy(sec, 100, 15000)
        trade, lots = a.record_sell(sec, 50, 18000)
        assert trade.side == OrderSide.SELL
        assert a.holdings[sec].quantity == 50
        assert a.cash_balance_paise == 10_000_000_00 - (100 * 15000) + (50 * 18000)

    def test_sell_all_removes_holding(self):
        a = self._make()
        a.contribute(10_000_000_00)
        sec = uuid.uuid4()
        a.record_buy(sec, 100, 15000)
        a.record_sell(sec, 100, 18000)
        assert sec not in a.holdings

    def test_sell_no_holding(self):
        a = self._make()
        a.contribute(10_000_000_00)
        with pytest.raises(ValidationError, match="No holding"):
            a.record_sell(uuid.uuid4(), 10, 15000)

    def test_cash_ledger_tracking(self):
        a = self._make()
        a.contribute(10_000_000_00)
        sec = uuid.uuid4()
        a.record_buy(sec, 10, 15000)
        a.record_sell(sec, 10, 18000)
        a.withdraw(1_000_00)
        # contribution + buy_debit + sell_credit + withdrawal = 4 entries
        assert len(a.cash_ledger) == 4

    def test_events_emitted(self):
        a = self._make()
        a.contribute(5_000_000_00)
        sec = uuid.uuid4()
        a.record_buy(sec, 10, 15000)
        evts = a.pull_events()
        assert len(evts) == 2  # CapitalFlowRecorded + TradeExecuted


# ── Client provisioning ────────────────────────────────────────────────

class TestClient:
    def test_provision(self):
        c = Client.provision(
            onboarding_application_id=uuid.uuid4(),
            client_code="PMS-ABC123",
            pan_hash="deadbeef",
            investor_type="individual",
            full_name="Test User",
            email="test@example.com",
        )
        assert c.status == ClientStatus.ACTIVE
        assert c.client_code == "PMS-ABC123"
        events = c.pull_events()
        assert len(events) == 1
        assert events[0].client_code == "PMS-ABC123"
