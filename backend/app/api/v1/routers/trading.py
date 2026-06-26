"""Trading endpoints -- orders, allocations, trades (blotter)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, date as date_type

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.audit.audit_logger import AuditLogger
from app.infrastructure.db.models_trading import OrderModel, OrderAllocationModel, TradeModel
from app.infrastructure.db.models_portfolio import PortfolioAccountModel
from app.infrastructure.db.models_client import ClientModel
from app.infrastructure.db.models_reference import SecurityModel
from app.services.notifications import TradeEvent, notify_trade_confirmation

_log = logging.getLogger("pms.trading.api")

router = APIRouter(prefix="/trading", tags=["trading"])


# -- Schemas ----------------------------------------------------------------

class OrderCreate(BaseModel):
    strategy_id: uuid.UUID
    security_id: uuid.UUID
    side: str  # buy | sell
    quantity: float
    order_type: str = "market"
    limit_price_paise: int | None = None


class OrderOut(BaseModel):
    id: uuid.UUID
    strategy_id: uuid.UUID
    security_id: uuid.UUID
    side: str
    quantity: float
    order_type: str
    limit_price_paise: int | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrderDecision(BaseModel):
    approve: bool
    reason: str | None = None


class AllocationCreate(BaseModel):
    portfolio_account_id: uuid.UUID
    allocated_qty: float


class AllocationOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    portfolio_account_id: uuid.UUID
    allocated_qty: float

    class Config:
        from_attributes = True


class TradeCreate(BaseModel):
    order_id: uuid.UUID | None = None
    portfolio_account_id: uuid.UUID
    security_id: uuid.UUID
    broker_id: uuid.UUID
    side: str
    quantity: float
    price_paise: int
    contract_note: str | None = None


class TradeOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID | None = None
    portfolio_account_id: uuid.UUID
    security_id: uuid.UUID
    broker_id: uuid.UUID
    side: str
    quantity: float
    price_paise: int
    traded_at: datetime
    contract_note: str | None = None

    class Config:
        from_attributes = True


# -- Orders -----------------------------------------------------------------

@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str | None = None,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    stmt = select(OrderModel)
    if status:
        stmt = stmt.where(OrderModel.status == status)
    stmt = stmt.order_by(desc(OrderModel.created_at)).limit(200)
    return db.scalars(stmt).all()


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(
    body: OrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(deps.require_staff),
):
    order = OrderModel(
        strategy_id=body.strategy_id,
        security_id=body.security_id,
        side=body.side,
        quantity=body.quantity,
        order_type=body.order_type,
        limit_price_paise=body.limit_price_paise,
        status="pending_approval",
    )
    db.add(order)
    db.flush()

    AuditLogger(db).log(
        event_type="order.created",
        description="Order created: " + body.side.upper() + " " + str(body.quantity),
        actor_id=user.get("sub"), actor_role=user.get("role"),
        resource_type="order", resource_id=str(order.id),
        details={"side": body.side, "quantity": body.quantity, "order_type": body.order_type},
        request=request,
    )
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/decide", response_model=OrderOut)
def decide_order(
    order_id: uuid.UUID,
    body: OrderDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(deps.require_compliance),
):
    order = db.get(OrderModel, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != "pending_approval":
        raise HTTPException(409, "Order already decided (status=" + order.status + ")")
    decision = "approved" if body.approve else "rejected"
    order.status = decision

    AuditLogger(db).log(
        event_type="order." + decision,
        description="Order " + decision + (": " + body.reason if body.reason else ""),
        actor_id=user.get("sub"), actor_role="compliance",
        resource_type="order", resource_id=str(order_id),
        details={"decision": decision, "reason": body.reason},
        request=request,
    )
    db.commit()
    db.refresh(order)
    return order


# -- Allocations ------------------------------------------------------------

@router.get("/orders/{order_id}/allocations", response_model=list[AllocationOut])
def list_allocations(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    stmt = select(OrderAllocationModel).where(OrderAllocationModel.order_id == order_id)
    return db.scalars(stmt).all()


@router.post("/orders/{order_id}/allocations", response_model=AllocationOut, status_code=201)
def add_allocation(
    order_id: uuid.UUID,
    body: AllocationCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    alloc = OrderAllocationModel(
        order_id=order_id,
        portfolio_account_id=body.portfolio_account_id,
        allocated_qty=body.allocated_qty,
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)
    return alloc


# -- Trades (blotter) -------------------------------------------------------

@router.get("/trades", response_model=list[TradeOut])
def list_trades(
    portfolio_account_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    stmt = select(TradeModel)
    if portfolio_account_id:
        stmt = stmt.where(TradeModel.portfolio_account_id == portfolio_account_id)
    stmt = stmt.order_by(desc(TradeModel.traded_at)).limit(500)
    return db.scalars(stmt).all()


@router.post("/trades", response_model=TradeOut, status_code=201)
def record_trade(
    body: TradeCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(deps.require_staff),
):
    trade = TradeModel(
        order_id=body.order_id,
        portfolio_account_id=body.portfolio_account_id,
        security_id=body.security_id,
        broker_id=body.broker_id,
        side=body.side,
        quantity=body.quantity,
        price_paise=body.price_paise,
        contract_note=body.contract_note,
    )
    db.add(trade)
    db.flush()

    price_inr = body.price_paise / 100
    AuditLogger(db).log(
        event_type="trade.recorded",
        description="Trade recorded: " + body.side.upper() + " " + str(body.quantity) + " @ INR " + str(price_inr),
        actor_id=user.get("sub"), actor_role=user.get("role"),
        resource_type="trade", resource_id=str(trade.id),
        details={"side": body.side, "quantity": body.quantity, "price_paise": body.price_paise,
                 "portfolio_account_id": str(body.portfolio_account_id)},
        request=request,
    )
    db.commit()
    db.refresh(trade)

    # -- Best-effort trade notification
    try:
        acct = db.get(PortfolioAccountModel, body.portfolio_account_id)
        client = db.get(ClientModel, acct.client_id) if acct else None
        sec = db.get(SecurityModel, body.security_id)
        if client and sec and acct:
            notify_trade_confirmation(TradeEvent(
                client_name=client.full_name,
                email=client.email,
                phone=client.mobile,
                account_code=acct.account_code,
                security_symbol=sec.symbol,
                side=body.side,
                quantity=body.quantity,
                price_inr=body.price_paise / 100,
                trade_date=trade.traded_at.date() if trade.traded_at else date_type.today(),
                order_id=str(body.order_id) if body.order_id else None,
            ))
    except Exception as exc:
        _log.warning("Trade notification failed: %s", exc)

    return trade
