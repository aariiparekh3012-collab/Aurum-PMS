"""SQLAlchemy implementations of portfolio repository ports."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session, joinedload

from app.domain.portfolio.entities import (
    CapitalFlow, CashLedgerEntry, Client, Holding, HoldingLot,
    PortfolioAccount, Trade,
)
from app.domain.portfolio.enums import (
    AssetKind, CashEntryType, ClientStatus, FlowType, OrderSide, PortfolioStatus,
)
from app.domain.portfolio.repositories import (
    ClientRepository, PortfolioAccountRepository, TradeRepository,
)
from app.infrastructure.db.portfolio_models import (
    CapitalFlowModel, CashLedgerModel, ClientModel, HoldingLotModel,
    HoldingModel, PortfolioAccountModel, TradeModel,
)


# ── Client ──────────────────────────────────────────────────────────────

class SqlAlchemyClientRepository(ClientRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, client: Client) -> None:
        row = ClientModel(
            id=client.id,
            onboarding_application_id=client.onboarding_application_id,
            client_code=client.client_code,
            pan_hash=client.pan_hash,
            investor_type=client.investor_type,
            full_name=client.full_name,
            email=client.email,
            status=client.status.value,
            created_at=client.created_at,
        )
        self._db.add(row)

    def get(self, client_id: uuid.UUID) -> Client | None:
        row = self._db.get(ClientModel, client_id)
        return self._to_entity(row) if row else None

    def get_by_pan_hash(self, pan_hash: str) -> Client | None:
        row = self._db.query(ClientModel).filter_by(pan_hash=pan_hash).first()
        return self._to_entity(row) if row else None

    def get_by_onboarding_id(self, app_id: uuid.UUID) -> Client | None:
        row = (
            self._db.query(ClientModel)
            .filter_by(onboarding_application_id=app_id)
            .first()
        )
        return self._to_entity(row) if row else None

    def list_all(self) -> list[Client]:
        rows = self._db.query(ClientModel).order_by(ClientModel.created_at.desc()).all()
        return [self._to_entity(r) for r in rows]

    @staticmethod
    def _to_entity(row: ClientModel) -> Client:
        return Client(
            id=row.id,
            onboarding_application_id=row.onboarding_application_id,
            client_code=row.client_code,
            pan_hash=row.pan_hash,
            investor_type=row.investor_type,
            full_name=row.full_name,
            email=row.email,
            status=ClientStatus(row.status),
            created_at=row.created_at,
        )


# ── Portfolio Account ───────────────────────────────────────────────────

class SqlAlchemyPortfolioAccountRepository(PortfolioAccountRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, account: PortfolioAccount) -> None:
        row = PortfolioAccountModel(
            id=account.id,
            client_id=account.client_id,
            strategy_id=account.strategy_id,
            demat_account_id=account.demat_account_id,
            fee_schedule_id=account.fee_schedule_id,
            account_code=account.account_code,
            status=account.status.value,
            inception_date=account.inception_date,
            cash_balance_paise=account.cash_balance_paise,
        )
        self._db.add(row)
        self._db.flush()

    def get(self, account_id: uuid.UUID) -> PortfolioAccount | None:
        row = (
            self._db.query(PortfolioAccountModel)
            .options(
                joinedload(PortfolioAccountModel.holdings)
                .joinedload(HoldingModel.lots),
            )
            .filter_by(id=account_id)
            .first()
        )
        return self._to_entity(row) if row else None

    def list_by_client(self, client_id: uuid.UUID) -> list[PortfolioAccount]:
        rows = (
            self._db.query(PortfolioAccountModel)
            .filter_by(client_id=client_id)
            .order_by(PortfolioAccountModel.inception_date.desc())
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def update(self, account: PortfolioAccount) -> None:
        row = self._db.get(PortfolioAccountModel, account.id)
        if row is None:
            return
        row.status = account.status.value
        row.cash_balance_paise = account.cash_balance_paise

        # Sync holdings
        existing_holdings = {h.security_id: h for h in row.holdings}
        for sec_id, domain_holding in account.holdings.items():
            if sec_id in existing_holdings:
                h_row = existing_holdings[sec_id]
                h_row.quantity = domain_holding.quantity
                h_row.avg_cost_paise = domain_holding.avg_cost_paise
                # replace lots
                h_row.lots.clear()
                for lot in domain_holding.lots:
                    h_row.lots.append(HoldingLotModel(
                        id=lot.id, quantity=lot.quantity,
                        cost_paise=lot.cost_paise, acquired_on=lot.acquired_on,
                    ))
            else:
                h_row = HoldingModel(
                    id=domain_holding.id,
                    portfolio_account_id=account.id,
                    security_id=sec_id,
                    quantity=domain_holding.quantity,
                    avg_cost_paise=domain_holding.avg_cost_paise,
                )
                for lot in domain_holding.lots:
                    h_row.lots.append(HoldingLotModel(
                        id=lot.id, quantity=lot.quantity,
                        cost_paise=lot.cost_paise, acquired_on=lot.acquired_on,
                    ))
                row.holdings.append(h_row)

        # Remove holdings that no longer exist in domain
        for sec_id in list(existing_holdings.keys()):
            if sec_id not in account.holdings:
                self._db.delete(existing_holdings[sec_id])

        # Persist new capital flows
        for flow in account.capital_flows:
            existing = self._db.get(CapitalFlowModel, flow.id)
            if existing is None:
                self._db.add(CapitalFlowModel(
                    id=flow.id, portfolio_account_id=account.id,
                    flow_type=flow.flow_type.value, asset_kind=flow.asset_kind.value,
                    amount_paise=flow.amount_paise, value_date=flow.value_date,
                ))

        # Persist new cash ledger entries (compute running balance)
        for entry in account.cash_ledger:
            existing = self._db.get(CashLedgerModel, entry.id)
            if existing is None:
                from sqlalchemy import func as _func, select as _select
                prev_balance = self._db.scalar(
                    _select(_func.coalesce(_func.sum(CashLedgerModel.amount_paise), 0))
                    .where(CashLedgerModel.portfolio_account_id == account.id)
                ) or 0
                self._db.add(CashLedgerModel(
                    id=entry.id, portfolio_account_id=account.id,
                    entry_type=entry.entry_type.value, amount_paise=entry.amount_paise,
                    balance_paise=prev_balance + entry.amount_paise,
                    posted_on=entry.posted_on, description=entry.description,
                ))

    def _to_entity(self, row: PortfolioAccountModel) -> PortfolioAccount:
        holdings: dict[uuid.UUID, Holding] = {}
        for h_row in (row.holdings or []):
            lots = [
                HoldingLot(
                    id=l.id, quantity=float(l.quantity),
                    cost_paise=l.cost_paise, acquired_on=l.acquired_on,
                )
                for l in h_row.lots
            ]
            holdings[h_row.security_id] = Holding(
                id=h_row.id,
                portfolio_account_id=h_row.portfolio_account_id,
                security_id=h_row.security_id,
                quantity=float(h_row.quantity),
                avg_cost_paise=h_row.avg_cost_paise,
                lots=lots,
            )
        return PortfolioAccount(
            id=row.id, client_id=row.client_id,
            strategy_id=row.strategy_id,
            demat_account_id=row.demat_account_id,
            fee_schedule_id=row.fee_schedule_id,
            account_code=row.account_code,
            status=PortfolioStatus(row.status),
            inception_date=row.inception_date,
            cash_balance_paise=row.cash_balance_paise,
            holdings=holdings,
        )


# ── Trade ───────────────────────────────────────────────────────────────

class SqlAlchemyTradeRepository(TradeRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, trade: Trade) -> None:
        self._db.add(TradeModel(
            id=trade.id, order_id=trade.order_id,
            portfolio_account_id=trade.portfolio_account_id,
            security_id=trade.security_id, broker_id=trade.broker_id,
            side=trade.side.value, quantity=trade.quantity,
            price_paise=trade.price_paise, traded_at=trade.traded_at,
        ))

    def list_by_portfolio(self, portfolio_id: uuid.UUID, *, limit: int = 50) -> list[Trade]:
        rows = (
            self._db.query(TradeModel)
            .filter_by(portfolio_account_id=portfolio_id)
            .order_by(TradeModel.traded_at.desc())
            .limit(limit)
            .all()
        )
        return [
            Trade(
                id=r.id, order_id=r.order_id,
                portfolio_account_id=r.portfolio_account_id,
                security_id=r.security_id, broker_id=r.broker_id,
                side=OrderSide(r.side), quantity=float(r.quantity),
                price_paise=r.price_paise, traded_at=r.traded_at,
            )
            for r in rows
        ]
