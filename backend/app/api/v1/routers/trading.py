"""Trading endpoints — orders, allocations, trades (blotter)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models_trading import OrderModel, OrderAllocationModel, TradeModel

router = APIRouter(prefix="/trading", tags=["trading"])


# ── Schemas ────────────────────────────────────────────────────────────────

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


# ── Orders ─────────────────────────────────────────────────────────────────

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
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
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
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/decide", response_model=OrderOut)
def decide_order(
    order_id: uuid.UUID,
    body: OrderDecision,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    order = db.get(OrderModel, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != "pending_approval":
        raise HTTPException(409, f"Order already decided (status={order.status})")
    order.status = "approved" if body.approve else "rejected"
    db.commit()
    db.refresh(order)
    return order


# ── Allocations ────────────────────────────────────────────────────────────

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


# ── Trades (blotter) ──────────────────────────────────────────────────────

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
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
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
    db.commit()
    db.refresh(trade)
    return trade
