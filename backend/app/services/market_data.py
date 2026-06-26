"""Market data service — parse bhavcopy CSVs and run daily mark-to-market.

Responsibilities:
  1. Parse downloaded NSE CM-UDiFF bhavcopy ZIPs into close-price lookups.
  2. Upsert close prices into a `reference.security_prices` table.
  3. Run a daily valuation job that marks every active portfolio to market
     and records valuation snapshots + return computations.

Designed to run as a post-download hook in the bhavcopy scheduler, or
manually via the `/api/v1/market-data/…` endpoints.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.application.performance.compute import (
    ComputeSnapshotCommand,
    ComputeSnapshotUseCase,
    ComputeReturnsCommand,
    ComputeReturnsUseCase,
)
from app.infrastructure.db.models_portfolio import (
    HoldingModel,
    PortfolioAccountModel,
)
from app.infrastructure.db.models_reference import SecurityModel
from app.infrastructure.db.models_market_data import SecurityPriceModel

logger = logging.getLogger(__name__)


# ── Bhavcopy CSV parser ──────────────────────────────────────────────────────

# NSE CM-UDiFF bhavcopy CSV columns we care about:
#   TckrSymb  —  trading symbol (e.g. RELIANCE)
#   ISIN      —  12-char ISIN
#   ClsPric   —  closing price (rupees, float)
#   LastPric  —  last traded price
#   TtlTradgVol — volume
#   SctySrs   —  series (EQ, BE, etc.)

def parse_bhavcopy_zip(zip_path: str | Path) -> list[dict]:
    """Extract rows from a bhavcopy ZIP, returning dicts with symbol/isin/close."""
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"Bhavcopy ZIP not found: {zip_path}")

    rows: list[dict] = []
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            logger.warning("No CSV found inside %s", zip_path.name)
            return rows

        with zf.open(csv_names[0]) as f:
            text = io.TextIOWrapper(f, encoding="utf-8")
            reader = csv.DictReader(text)
            for row in reader:
                # Normalise column names (strip whitespace)
                row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}

                symbol = row.get("TckrSymb") or row.get("SYMBOL") or ""
                isin = row.get("ISIN") or ""
                series = row.get("SctySrs") or row.get("SERIES") or ""

                # Only equity series
                if series not in ("EQ", "BE", "BZ", "SM", "ST"):
                    continue

                # Parse close price
                close_str = row.get("ClsPric") or row.get("CLOSE_PRICE") or row.get("CLOSE") or ""
                try:
                    close_price = float(close_str)
                except (ValueError, TypeError):
                    continue

                if close_price <= 0:
                    continue

                rows.append({
                    "symbol": symbol.upper(),
                    "isin": isin.upper(),
                    "close_price": close_price,
                    "close_price_paise": int(round(close_price * 100)),
                    "volume": _safe_int(row.get("TtlTradgVol") or row.get("TTL_TRD_QNTY") or "0"),
                })

    logger.info("Parsed %d equity rows from %s", len(rows), zip_path.name)
    return rows


def _safe_int(s: str) -> int:
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


# ── Price persistence ────────────────────────────────────────────────────────

def upsert_prices(db: Session, trade_date: dt.date, parsed_rows: list[dict]) -> int:
    """Match parsed bhavcopy rows to securities_master and upsert prices.

    Returns count of prices upserted.
    """
    if not parsed_rows:
        return 0

    # Build ISIN → security_id map from reference.securities_master
    all_securities = db.scalars(
        select(SecurityModel).where(SecurityModel.is_active.is_(True))
    ).all()
    isin_map: dict[str, uuid.UUID] = {s.isin.upper(): s.id for s in all_securities}
    symbol_map: dict[str, uuid.UUID] = {s.symbol.upper(): s.id for s in all_securities}

    count = 0
    for row in parsed_rows:
        sec_id = isin_map.get(row["isin"]) or symbol_map.get(row["symbol"])
        if sec_id is None:
            continue  # security not in our master — skip

        existing = db.scalar(
            select(SecurityPriceModel).where(
                and_(
                    SecurityPriceModel.security_id == sec_id,
                    SecurityPriceModel.price_date == trade_date,
                )
            )
        )
        if existing:
            existing.close_price_paise = row["close_price_paise"]
            existing.volume = row["volume"]
        else:
            db.add(SecurityPriceModel(
                security_id=sec_id,
                price_date=trade_date,
                close_price_paise=row["close_price_paise"],
                volume=row["volume"],
            ))
        count += 1

    db.flush()
    logger.info("Upserted %d security prices for %s", count, trade_date)
    return count


def get_latest_prices(db: Session, as_of: dt.date | None = None) -> dict[uuid.UUID, int]:
    """Return {security_id: close_price_paise} for the most recent date ≤ as_of."""
    if as_of is None:
        as_of = dt.date.today()

    # Get the most recent price date
    from sqlalchemy import func
    latest_date = db.scalar(
        select(func.max(SecurityPriceModel.price_date)).where(
            SecurityPriceModel.price_date <= as_of
        )
    )
    if latest_date is None:
        return {}

    rows = db.scalars(
        select(SecurityPriceModel).where(
            SecurityPriceModel.price_date == latest_date
        )
    ).all()

    return {r.security_id: r.close_price_paise for r in rows}


# ── Daily valuation job ──────────────────────────────────────────────────────

def run_daily_valuation(db: Session, as_of: dt.date | None = None) -> int:
    """Mark all active portfolio accounts to market using latest prices.

    Creates valuation snapshots and recomputes period returns for each account.
    Returns number of accounts processed.
    """
    if as_of is None:
        as_of = dt.date.today()

    prices = get_latest_prices(db, as_of)
    if not prices:
        logger.warning("No market prices available for %s — skipping valuation", as_of)
        return 0

    # Get all active portfolio accounts that have holdings
    accounts = db.scalars(
        select(PortfolioAccountModel).where(
            PortfolioAccountModel.status == "active"
        )
    ).all()

    count = 0
    for account in accounts:
        holdings = db.scalars(
            select(HoldingModel).where(
                HoldingModel.portfolio_account_id == account.id
            )
        ).all()

        if not holdings:
            continue

        # Build price map for this account's holdings
        account_prices: dict[uuid.UUID, int] = {}
        for h in holdings:
            if h.security_id in prices:
                account_prices[h.security_id] = prices[h.security_id]
            # If no market price, ComputeSnapshotUseCase falls back to avg_cost

        try:
            # Record valuation snapshot
            snap_uc = ComputeSnapshotUseCase(db)
            snap_uc.execute(ComputeSnapshotCommand(
                portfolio_account_id=account.id,
                as_of=as_of,
                prices=account_prices,
            ))

            # Recompute returns
            ret_uc = ComputeReturnsUseCase(db)
            ret_uc.execute(ComputeReturnsCommand(
                portfolio_account_id=account.id,
                as_of=as_of,
            ))

            count += 1
        except Exception as exc:
            logger.error(
                "Valuation failed for account %s: %s",
                account.account_code, exc,
            )

    db.commit()
    logger.info("Daily valuation complete: %d accounts processed for %s", count, as_of)
    return count
