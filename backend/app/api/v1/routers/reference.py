"""CRUD endpoints for reference / master data (securities, strategies, brokers, benchmarks)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models_reference import (
    BenchmarkModel,
    BrokerModel,
    SecurityModel,
    StrategyConstituentModel,
    StrategyModel,
)

router = APIRouter(prefix="/reference", tags=["reference"])


# ── Schemas ────────────────────────────────────────────────────────────────

class SecurityOut(BaseModel):
    id: uuid.UUID
    isin: str
    symbol: str
    exchange: str
    instrument_type: str
    sector: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class SecurityCreate(BaseModel):
    isin: str
    symbol: str
    exchange: str = "NSE"
    instrument_type: str = "equity"
    sector: str | None = None


class StrategyOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    approach: str
    benchmark_id: uuid.UUID | None = None
    is_active: bool

    class Config:
        from_attributes = True


class StrategyCreate(BaseModel):
    name: str
    code: str
    approach: str
    benchmark_id: uuid.UUID | None = None


class BrokerOut(BaseModel):
    id: uuid.UUID
    name: str
    sebi_reg_no: str
    is_active: bool

    class Config:
        from_attributes = True


class BrokerCreate(BaseModel):
    name: str
    sebi_reg_no: str


class BenchmarkOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    class Config:
        from_attributes = True


class BenchmarkCreate(BaseModel):
    name: str
    code: str


class ConstituentCreate(BaseModel):
    security_id: uuid.UUID
    target_weight: float


class ConstituentOut(BaseModel):
    id: uuid.UUID
    strategy_id: uuid.UUID
    security_id: uuid.UUID
    target_weight: float

    class Config:
        from_attributes = True


class SeedResult(BaseModel):
    securities: int
    benchmarks: int
    strategies: int
    brokers: int


# ── Securities ─────────────────────────────────────────────────────────────

@router.get("/securities", response_model=list[SecurityOut])
def list_securities(
    q: str = Query("", description="Search symbol or ISIN"),
    active_only: bool = True,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.get_current_user),
):
    stmt = select(SecurityModel)
    if active_only:
        stmt = stmt.where(SecurityModel.is_active.is_(True))
    if q:
        pattern = f"%{q.upper()}%"
        stmt = stmt.where(
            SecurityModel.symbol.ilike(pattern) | SecurityModel.isin.ilike(pattern)
        )
    stmt = stmt.order_by(SecurityModel.symbol).limit(200)
    return db.scalars(stmt).all()


@router.post("/securities", response_model=SecurityOut, status_code=201)
def create_security(
    body: SecurityCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    sec = SecurityModel(
        isin=body.isin.upper(),
        symbol=body.symbol.upper(),
        exchange=body.exchange.upper(),
        instrument_type=body.instrument_type,
        sector=body.sector,
    )
    db.add(sec)
    db.commit()
    db.refresh(sec)
    return sec


# ── Benchmarks ─────────────────────────────────────────────────────────────

@router.get("/benchmarks", response_model=list[BenchmarkOut])
def list_benchmarks(
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.get_current_user),
):
    return db.scalars(select(BenchmarkModel).order_by(BenchmarkModel.code)).all()


@router.post("/benchmarks", response_model=BenchmarkOut, status_code=201)
def create_benchmark(
    body: BenchmarkCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    bm = BenchmarkModel(name=body.name, code=body.code.upper())
    db.add(bm)
    db.commit()
    db.refresh(bm)
    return bm


# ── Strategies ─────────────────────────────────────────────────────────────

@router.get("/strategies", response_model=list[StrategyOut])
def list_strategies(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.get_current_user),
):
    stmt = select(StrategyModel)
    if active_only:
        stmt = stmt.where(StrategyModel.is_active.is_(True))
    return db.scalars(stmt.order_by(StrategyModel.name)).all()


@router.post("/strategies", response_model=StrategyOut, status_code=201)
def create_strategy(
    body: StrategyCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    s = StrategyModel(
        name=body.name,
        code=body.code.upper(),
        approach=body.approach,
        benchmark_id=body.benchmark_id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("/strategies/{strategy_id}/constituents", response_model=list[ConstituentOut])
def list_constituents(
    strategy_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.get_current_user),
):
    stmt = select(StrategyConstituentModel).where(
        StrategyConstituentModel.strategy_id == strategy_id
    )
    return db.scalars(stmt).all()


@router.post("/strategies/{strategy_id}/constituents", response_model=ConstituentOut, status_code=201)
def add_constituent(
    strategy_id: uuid.UUID,
    body: ConstituentCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    c = StrategyConstituentModel(
        strategy_id=strategy_id,
        security_id=body.security_id,
        target_weight=body.target_weight,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ── Brokers ────────────────────────────────────────────────────────────────

@router.get("/brokers", response_model=list[BrokerOut])
def list_brokers(
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.get_current_user),
):
    return db.scalars(select(BrokerModel).order_by(BrokerModel.name)).all()


@router.post("/brokers", response_model=BrokerOut, status_code=201)
def create_broker(
    body: BrokerCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    b = BrokerModel(name=body.name, sebi_reg_no=body.sebi_reg_no.upper())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


# ── Seed ───────────────────────────────────────────────────────────────────

SEED_SECURITIES = [
    ("INE002A01018", "RELIANCE", "NSE", "equity", "Energy"),
    ("INE009A01021", "INFY", "NSE", "equity", "IT"),
    ("INE467B01029", "TCS", "NSE", "equity", "IT"),
    ("INE040A01034", "HDFC", "NSE", "equity", "Financials"),
    ("INE090A01021", "ICICIBANK", "NSE", "equity", "Financials"),
    ("INE154A01025", "ITC", "NSE", "equity", "FMCG"),
    ("INE030A01027", "HINDUNILVR", "NSE", "equity", "FMCG"),
    ("INE585B01010", "MARUTI", "NSE", "equity", "Automobile"),
    ("INE397D01024", "BHARTIARTL", "NSE", "equity", "Telecom"),
    ("INE028A01039", "BAJFINANCE", "NSE", "equity", "Financials"),
    ("INE019A01038", "WIPRO", "NSE", "equity", "IT"),
    ("INE062A01020", "SBIN", "NSE", "equity", "Financials"),
    ("INE018A01030", "HCLTECH", "NSE", "equity", "IT"),
    ("INE476A01014", "TITAN", "NSE", "equity", "Consumer"),
    ("INE669E01016", "ADANIENT", "NSE", "equity", "Conglomerate"),
]

SEED_BENCHMARKS = [
    ("NIFTY 50", "NIFTY50"),
    ("BSE SENSEX", "SENSEX"),
    ("NIFTY 500", "NIFTY500"),
]

SEED_BROKERS = [
    ("Zerodha Broking", "INZ000031633"),
    ("ICICI Securities", "INZ000183631"),
    ("HDFC Securities", "INZ000186937"),
]


@router.post("/seed", response_model=SeedResult)
def seed_reference_data(
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_compliance),
):
    """Upsert sample NSE securities, benchmarks, strategies, brokers."""
    sec_count = 0
    for isin, symbol, exchange, itype, sector in SEED_SECURITIES:
        exists = db.scalar(select(SecurityModel).where(SecurityModel.isin == isin))
        if not exists:
            db.add(SecurityModel(isin=isin, symbol=symbol, exchange=exchange, instrument_type=itype, sector=sector))
            sec_count += 1

    bm_count = 0
    bm_ids: dict[str, uuid.UUID] = {}
    for name, code in SEED_BENCHMARKS:
        existing = db.scalar(select(BenchmarkModel).where(BenchmarkModel.code == code))
        if existing:
            bm_ids[code] = existing.id
        else:
            bm = BenchmarkModel(name=name, code=code)
            db.add(bm)
            db.flush()
            bm_ids[code] = bm.id
            bm_count += 1

    strat_count = 0
    strategies_seed = [
        ("Large Cap Value", "LCV", "value", "NIFTY50"),
        ("Multi Cap Growth", "MCG", "growth", "NIFTY500"),
        ("Flexi Cap Core", "FCC", "flexi_cap", "NIFTY500"),
    ]
    for name, code, approach, bm_code in strategies_seed:
        exists = db.scalar(select(StrategyModel).where(StrategyModel.code == code))
        if not exists:
            db.add(StrategyModel(name=name, code=code, approach=approach, benchmark_id=bm_ids.get(bm_code)))
            strat_count += 1

    broker_count = 0
    for name, reg_no in SEED_BROKERS:
        exists = db.scalar(select(BrokerModel).where(BrokerModel.sebi_reg_no == reg_no))
        if not exists:
            db.add(BrokerModel(name=name, sebi_reg_no=reg_no))
            broker_count += 1

    db.commit()
    return SeedResult(securities=sec_count, benchmarks=bm_count, strategies=strat_count, brokers=broker_count)
