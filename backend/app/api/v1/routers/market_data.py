"""Market data endpoints — price ingestion, daily valuation trigger."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.core.database import get_db
from app.infrastructure.db.models_market_data import SecurityPriceModel
from app.infrastructure.db.models_nse_reports import NseBhavCopyReportModel
from app.infrastructure.db.nse_database import NseSessionLocal
from app.services.market_data import (
    get_latest_prices,
    parse_bhavcopy_zip,
    run_daily_valuation,
    upsert_prices,
)

router = APIRouter(prefix="/market-data", tags=["market-data"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PriceOut(BaseModel):
    security_id: uuid.UUID
    price_date: date
    close_price_paise: int
    volume: int

    class Config:
        from_attributes = True


class IngestResult(BaseModel):
    trade_date: date
    rows_parsed: int
    prices_upserted: int


class ValuationResult(BaseModel):
    as_of: date
    accounts_processed: int


class LatestPriceOut(BaseModel):
    security_id: uuid.UUID
    close_price_paise: int
    close_price_inr: float


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/ingest/{trade_date}", response_model=IngestResult)
def ingest_bhavcopy(
    trade_date: date,
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Parse a downloaded bhavcopy ZIP for the given date and upsert prices.

    Looks up the ZIP path from nse_bhavcopy_reports table.
    """
    # Look up the bhavcopy record from the NSE database
    nse_factory = NseSessionLocal()
    nse_db = nse_factory()
    try:
        report = nse_db.scalar(
            select(NseBhavCopyReportModel).where(
                NseBhavCopyReportModel.file_date == trade_date,
                NseBhavCopyReportModel.status == "downloaded",
            )
        )
    finally:
        nse_db.close()

    if report is None:
        raise HTTPException(
            404,
            f"No downloaded bhavcopy found for {trade_date}. "
            "Run the bhavcopy downloader first.",
        )

    rows = parse_bhavcopy_zip(report.file_path)
    count = upsert_prices(db, trade_date, rows)
    db.commit()

    return IngestResult(
        trade_date=trade_date,
        rows_parsed=len(rows),
        prices_upserted=count,
    )


@router.post("/valuate", response_model=ValuationResult)
def trigger_valuation(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Trigger daily mark-to-market valuation for all active portfolios."""
    target_date = as_of or date.today()
    count = run_daily_valuation(db, target_date)
    return ValuationResult(as_of=target_date, accounts_processed=count)


@router.get("/prices/latest", response_model=list[LatestPriceOut])
def latest_prices(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Get the latest available close prices for all tracked securities."""
    prices = get_latest_prices(db, as_of)
    return [
        LatestPriceOut(
            security_id=sec_id,
            close_price_paise=price,
            close_price_inr=price / 100,
        )
        for sec_id, price in prices.items()
    ]


@router.get("/prices/{security_id}", response_model=list[PriceOut])
def price_history(
    security_id: uuid.UUID,
    limit: int = Query(90, le=365),
    db: Session = Depends(get_db),
    _user: dict = Depends(deps.require_staff),
):
    """Get price history for a single security."""
    rows = db.scalars(
        select(SecurityPriceModel)
        .where(SecurityPriceModel.security_id == security_id)
        .order_by(desc(SecurityPriceModel.price_date))
        .limit(limit)
    ).all()
    return rows
