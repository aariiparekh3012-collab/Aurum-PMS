"""Use case: record a contribution or withdrawal."""
from __future__ import annotations
from app.application.portfolio.dto import CapitalFlowCommand
from app.core.exceptions import NotFoundError
from app.domain.portfolio.repositories import PortfolioAccountRepository


class RecordCapitalFlowUseCase:
    def __init__(self, portfolio_repo: PortfolioAccountRepository):
        self._portfolios = portfolio_repo

    def execute(self, cmd: CapitalFlowCommand) -> dict:
        account = self._portfolios.get(cmd.portfolio_account_id)
        if account is None:
            raise NotFoundError("Portfolio account not found")

        amount_paise = round(cmd.amount_inr * 100)
        if cmd.flow_type == "contribution":
            flow = account.contribute(amount_paise)
        else:
            flow = account.withdraw(amount_paise)

        self._portfolios.update(account)
        return {
            "id": str(flow.id), "flow_type": flow.flow_type.value,
            "amount_inr": flow.amount_paise / 100,
            "cash_balance_inr": account.cash_balance_paise / 100,
        }
