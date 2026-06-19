"""Tests for portfolio use cases using in-memory repository fakes."""
from __future__ import annotations

import uuid
import datetime as dt
import pytest

from app.domain.portfolio.entities import Client, PortfolioAccount, Trade
from app.domain.portfolio.enums import ClientStatus, OrderSide, PortfolioStatus
from app.domain.portfolio.repositories import (
    ClientRepository, PortfolioAccountRepository, TradeRepository,
)
from app.domain.onboarding.entities import OnboardingApplication
from app.domain.onboarding.enums import OnboardingStatus, InvestorType
from app.domain.onboarding.value_objects import PAN, Money
from app.domain.onboarding.repositories import OnboardingRepository

from app.application.portfolio.dto import (
    ProvisionClientCommand, CreatePortfolioCommand,
    RecordTradeCommand, CapitalFlowCommand,
)
from app.application.portfolio.use_cases.provision_client import ProvisionClientUseCase
from app.application.portfolio.use_cases.create_portfolio import CreatePortfolioUseCase
from app.application.portfolio.use_cases.record_trade import RecordTradeUseCase
from app.application.portfolio.use_cases.record_capital_flow import RecordCapitalFlowUseCase
from app.core.exceptions import NotFoundError, ValidationError


# ── In-memory fakes ────────────────────────────────────────────────────

class FakeOnboardingRepo(OnboardingRepository):
    def __init__(self):
        self._store: dict[uuid.UUID, OnboardingApplication] = {}

    def add(self, app):
        self._store[app.id] = app
    def get(self, app_id):
        return self._store.get(app_id)
    def get_by_pan(self, pan_hash):
        return None
    def update(self, app):
        self._store[app.id] = app
    def list_by_status(self, status, *, limit=50, offset=0):
        return [a for a in self._store.values() if a.status == status]
    def count_by_status(self, status):
        return len(self.list_by_status(status))


class FakeClientRepo(ClientRepository):
    def __init__(self):
        self._store: dict[uuid.UUID, Client] = {}

    def add(self, client):
        self._store[client.id] = client
    def get(self, client_id):
        return self._store.get(client_id)
    def get_by_pan_hash(self, pan_hash):
        for c in self._store.values():
            if c.pan_hash == pan_hash:
                return c
        return None
    def get_by_onboarding_id(self, app_id):
        for c in self._store.values():
            if c.onboarding_application_id == app_id:
                return c
        return None


class FakePortfolioRepo(PortfolioAccountRepository):
    def __init__(self):
        self._store: dict[uuid.UUID, PortfolioAccount] = {}

    def add(self, account):
        self._store[account.id] = account
    def get(self, account_id):
        return self._store.get(account_id)
    def list_by_client(self, client_id):
        return [a for a in self._store.values() if a.client_id == client_id]
    def update(self, account):
        self._store[account.id] = account


class FakeTradeRepo(TradeRepository):
    def __init__(self):
        self._store: list[Trade] = []

    def add(self, trade):
        self._store.append(trade)
    def list_by_portfolio(self, portfolio_id, *, limit=50):
        return [t for t in self._store if t.portfolio_account_id == portfolio_id][:limit]


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_active_onboarding(repo: FakeOnboardingRepo) -> OnboardingApplication:
    """Create an onboarding app and force it to ACTIVE."""
    app = OnboardingApplication(
        investor_type=InvestorType.INDIVIDUAL,
        full_name="Test Investor",
        email="test@example.com",
        pan=PAN("ABCDE1234F"),
        mobile="+919876543210",
        proposed_investment=Money(50_00_000),
    )
    # Force status to ACTIVE for testing
    app.status = OnboardingStatus.ACTIVE
    repo.add(app)
    return app


# ── ProvisionClientUseCase ──────────────────────────────────────────────

class TestProvisionClient:
    def test_success(self):
        onb = FakeOnboardingRepo()
        clients = FakeClientRepo()
        app = _make_active_onboarding(onb)

        uc = ProvisionClientUseCase(onboarding_repo=onb, client_repo=clients)
        view = uc.execute(ProvisionClientCommand(onboarding_application_id=app.id))

        assert view.full_name == "Test Investor"
        assert view.status == "active"
        assert view.client_code.startswith("PMS-")

    def test_not_active_raises(self):
        onb = FakeOnboardingRepo()
        clients = FakeClientRepo()
        app = OnboardingApplication(
            investor_type=InvestorType.INDIVIDUAL,
            full_name="Draft User", email="d@e.com",
            pan=PAN("ABCDE1234F"), mobile="+919876543210",
            proposed_investment=Money(50_00_000),
        )
        onb.add(app)  # status=DRAFT

        uc = ProvisionClientUseCase(onboarding_repo=onb, client_repo=clients)
        with pytest.raises(ValidationError, match="must be active"):
            uc.execute(ProvisionClientCommand(onboarding_application_id=app.id))

    def test_already_provisioned(self):
        onb = FakeOnboardingRepo()
        clients = FakeClientRepo()
        app = _make_active_onboarding(onb)

        uc = ProvisionClientUseCase(onboarding_repo=onb, client_repo=clients)
        uc.execute(ProvisionClientCommand(onboarding_application_id=app.id))
        with pytest.raises(ValidationError, match="already provisioned"):
            uc.execute(ProvisionClientCommand(onboarding_application_id=app.id))

    def test_not_found(self):
        uc = ProvisionClientUseCase(
            onboarding_repo=FakeOnboardingRepo(), client_repo=FakeClientRepo(),
        )
        with pytest.raises(NotFoundError):
            uc.execute(ProvisionClientCommand(onboarding_application_id=uuid.uuid4()))


# ── CreatePortfolioUseCase ──────────────────────────────────────────────

class TestCreatePortfolio:
    def test_success(self):
        clients = FakeClientRepo()
        portfolios = FakePortfolioRepo()
        c = Client.provision(
            onboarding_application_id=uuid.uuid4(), client_code="PMS-TEST",
            pan_hash="abc", investor_type="individual",
            full_name="Test", email="t@t.com",
        )
        clients.add(c)

        uc = CreatePortfolioUseCase(client_repo=clients, portfolio_repo=portfolios)
        view = uc.execute(CreatePortfolioCommand(
            client_id=c.id, strategy_id=uuid.uuid4(),
        ))
        assert view.account_code.startswith("PA-")
        assert view.status == "pending"

    def test_client_not_found(self):
        uc = CreatePortfolioUseCase(
            client_repo=FakeClientRepo(), portfolio_repo=FakePortfolioRepo(),
        )
        with pytest.raises(NotFoundError):
            uc.execute(CreatePortfolioCommand(
                client_id=uuid.uuid4(), strategy_id=uuid.uuid4(),
            ))


# ── RecordTradeUseCase ──────────────────────────────────────────────────

class TestRecordTrade:
    def _setup(self):
        portfolios = FakePortfolioRepo()
        trades = FakeTradeRepo()
        acct = PortfolioAccount(
            client_id=uuid.uuid4(), strategy_id=uuid.uuid4(),
            account_code="PA-T1", inception_date=dt.date.today(),
        )
        acct.contribute(10_000_000_00)  # 1 crore paise = ₹1 lakh
        portfolios.add(acct)
        return portfolios, trades, acct

    def test_buy(self):
        portfolios, trades, acct = self._setup()
        sec = uuid.uuid4()
        uc = RecordTradeUseCase(portfolio_repo=portfolios, trade_repo=trades)
        view = uc.execute(RecordTradeCommand(
            portfolio_account_id=acct.id, security_id=sec,
            side="buy", quantity=10, price_inr=150.00,
        ))
        assert view.side == "buy"
        assert view.quantity == 10
        assert view.price_inr == 150.0

    def test_sell(self):
        portfolios, trades, acct = self._setup()
        sec = uuid.uuid4()
        uc = RecordTradeUseCase(portfolio_repo=portfolios, trade_repo=trades)
        uc.execute(RecordTradeCommand(
            portfolio_account_id=acct.id, security_id=sec,
            side="buy", quantity=100, price_inr=150.00,
        ))
        view = uc.execute(RecordTradeCommand(
            portfolio_account_id=acct.id, security_id=sec,
            side="sell", quantity=50, price_inr=180.00,
        ))
        assert view.side == "sell"
        assert view.quantity == 50

    def test_account_not_found(self):
        uc = RecordTradeUseCase(
            portfolio_repo=FakePortfolioRepo(), trade_repo=FakeTradeRepo(),
        )
        with pytest.raises(NotFoundError):
            uc.execute(RecordTradeCommand(
                portfolio_account_id=uuid.uuid4(), security_id=uuid.uuid4(),
                side="buy", quantity=10, price_inr=100,
            ))


# ── RecordCapitalFlowUseCase ───────────────────────────────────────────

class TestRecordCapitalFlow:
    def test_contribution(self):
        portfolios = FakePortfolioRepo()
        acct = PortfolioAccount(
            client_id=uuid.uuid4(), strategy_id=uuid.uuid4(),
            account_code="PA-CF", inception_date=dt.date.today(),
        )
        portfolios.add(acct)

        uc = RecordCapitalFlowUseCase(portfolio_repo=portfolios)
        result = uc.execute(CapitalFlowCommand(
            portfolio_account_id=acct.id, flow_type="contribution", amount_inr=50_000,
        ))
        assert result["flow_type"] == "contribution"
        assert result["cash_balance_inr"] == 50_000

    def test_withdrawal(self):
        portfolios = FakePortfolioRepo()
        acct = PortfolioAccount(
            client_id=uuid.uuid4(), strategy_id=uuid.uuid4(),
            account_code="PA-CF2", inception_date=dt.date.today(),
        )
        acct.contribute(100_000_00)
        portfolios.add(acct)

        uc = RecordCapitalFlowUseCase(portfolio_repo=portfolios)
        result = uc.execute(CapitalFlowCommand(
            portfolio_account_id=acct.id, flow_type="withdrawal", amount_inr=500,
        ))
        assert result["flow_type"] == "withdrawal"

    def test_account_not_found(self):
        uc = RecordCapitalFlowUseCase(portfolio_repo=FakePortfolioRepo())
        with pytest.raises(NotFoundError):
            uc.execute(CapitalFlowCommand(
                portfolio_account_id=uuid.uuid4(),
                flow_type="contribution", amount_inr=1000,
            ))
