"""Compatibility shim.

Historically this module defined its own ORM models in the ``public`` schema,
which duplicated the canonical schema-qualified models in ``models_*`` and broke
the SQLAlchemy registry ("Multiple classes found for ...").

It now simply re-exports the canonical models so existing imports keep working
while only ONE class per table is registered.
"""
from __future__ import annotations

from app.infrastructure.db.models_client import ClientModel
from app.infrastructure.db.models_reference import (
    SecurityModel,
    StrategyModel,
    BrokerModel,
)
from app.infrastructure.db.models_trading import (
    OrderModel,
    OrderAllocationModel,
    TradeModel,
)
from app.infrastructure.db.models_portfolio import (
    FeeScheduleModel,
    PortfolioAccountModel,
    HoldingModel,
    HoldingLotModel,
    CashLedgerModel,
    CapitalFlowModel,
)

__all__ = [
    "ClientModel",
    "SecurityModel",
    "StrategyModel",
    "BrokerModel",
    "OrderModel",
    "OrderAllocationModel",
    "TradeModel",
    "FeeScheduleModel",
    "PortfolioAccountModel",
    "HoldingModel",
    "HoldingLotModel",
    "CashLedgerModel",
    "CapitalFlowModel",
]
