"""Portfolio domain events."""
from __future__ import annotations
import datetime as dt
import uuid
from dataclasses import dataclass, field
from app.domain.onboarding.events import DomainEvent


@dataclass(frozen=True)
class ClientProvisioned(DomainEvent):
    client_code: str = ""

@dataclass(frozen=True)
class PortfolioAccountCreated(DomainEvent):
    account_code: str = ""
    strategy_name: str = ""

@dataclass(frozen=True)
class TradeExecuted(DomainEvent):
    side: str = ""
    security_isin: str = ""
    quantity: float = 0
    price_paise: int = 0

@dataclass(frozen=True)
class CapitalFlowRecorded(DomainEvent):
    flow_type: str = ""
    amount_paise: int = 0

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    side: str = ""
    security_isin: str = ""
    quantity: float = 0
