"""Use case: record a buy or sell trade on a portfolio."""
from __future__ import annotations
from app.application.portfolio.dto import RecordTradeCommand, TradeView
from app.core.exceptions import NotFoundError
from app.domain.portfolio.enums import OrderSide
from app.domain.portfolio.repositories import PortfolioAccountRepository, TradeRepository


class RecordTradeUseCase:
    def __init__(self, portfolio_repo: PortfolioAccountRepository, trade_repo: TradeRepository):
        self._portfolios = portfolio_repo
        self._trades = trade_repo

    def execute(self, cmd: RecordTradeCommand) -> TradeView:
        account = self._portfolios.get(cmd.portfolio_account_id)
        if account is None:
            raise NotFoundError("Portfolio account not found")

        price_paise = round(cmd.price_inr * 100)
        side = OrderSide(cmd.side)

        if side == OrderSide.BUY:
            trade = account.record_buy(cmd.security_id, cmd.quantity, price_paise)
        else:
            trade, _ = account.record_sell(cmd.security_id, cmd.quantity, price_paise)

        trade.order_id = cmd.order_id
        trade.broker_id = cmd.broker_id

        self._portfolios.update(account)
        self._trades.add(trade, contract_note=cmd.contract_note)
        return TradeView(
            id=trade.id, side=trade.side.value, security_name="",
            quantity=trade.quantity, price_inr=trade.price_paise / 100,
            value_inr=trade.value_paise / 100,
            traded_at=trade.traded_at.isoformat(),
        )
