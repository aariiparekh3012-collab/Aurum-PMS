"""Use case: create a portfolio account for a client under a strategy."""
from __future__ import annotations
import uuid
import datetime as dt
from app.application.portfolio.dto import CreatePortfolioCommand, PortfolioView
from app.core.exceptions import NotFoundError
from app.domain.portfolio.entities import PortfolioAccount
from app.domain.portfolio.repositories import ClientRepository, PortfolioAccountRepository


class CreatePortfolioUseCase:
    def __init__(self, client_repo: ClientRepository, portfolio_repo: PortfolioAccountRepository):
        self._clients = client_repo
        self._portfolios = portfolio_repo

    def execute(self, cmd: CreatePortfolioCommand) -> PortfolioView:
        client = self._clients.get(cmd.client_id)
        if client is None:
            raise NotFoundError("Client not found")

        account_code = f"PA-{uuid.uuid4().hex[:8].upper()}"
        account = PortfolioAccount(
            client_id=cmd.client_id, strategy_id=cmd.strategy_id,
            fee_schedule_id=cmd.fee_schedule_id, account_code=account_code,
            inception_date=dt.date.today(),
        )
        self._portfolios.add(account)
        return PortfolioView(
            id=account.id, account_code=account.account_code,
            strategy_name="", status=account.status.value,
            inception_date=str(account.inception_date),
            cash_balance_inr=0, invested_value_inr=0, holdings_count=0,
        )
