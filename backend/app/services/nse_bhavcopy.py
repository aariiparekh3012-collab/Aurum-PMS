"""NSE CM-UDiFF Common Bhavcopy downloader service.

Downloads the daily Bhavcopy ZIP from NSE at 8:00 PM IST every trading day.
Stores the file on disk and records metadata in the nse_bhavcopy_reports table.

NSE download flow:
  1. Hit NSE homepage to acquire session cookies.
  2. Call NSE reports API to get the actual download URL for the given date.
  3. Stream-download the ZIP to disk.
  4. Upsert a row in nse_bhavcopy_reports (unique on file_date — no overwrites).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.infrastructure.db.nse_database import NseSessionLocal
from app.infrastructure.db.models_nse_reports import NseBhavCopyReportModel

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Directory where ZIPs are stored; override via env var BHAVCOPY_STORE_DIR
_DEFAULT_STORE = Path(__file__).resolve().parents[3] / "bhavcopy_files"
STORE_DIR = Path(os.getenv("BHAVCOPY_STORE_DIR", str(_DEFAULT_STORE)))

NSE_HOME = "https://www.nseindia.com"
NSE_REPORTS_API = (
    "https://www.nseindia.com/api/reports"
    "?archives=%5B%7B%22name%22%3A%22CM%20-%20UDiFF%20Common%20Bhavcopy%20Final%20%28zip%29%22"
    "%2C%22type%22%3A%22daily%22%2C%22category%22%3A%22capital-market%22"
    "%2C%22section%22%3A%22equities%22%7D%5D"
    "&date={date}&type=equities&mode=single"
)
# Fallback direct archives URL (works without session on some environments)
NSE_ARCHIVES_URL = (
    "https://nsearchives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{date_nodash}_F_0000.csv.zip"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}


# ---------------------------------------------------------------------------
# Core downloader
# ---------------------------------------------------------------------------

def _file_name(trade_date: dt.date) -> str:
    return f"BhavCopy_NSE_CM_0_0_0_{trade_date.strftime('%Y%m%d')}_F_0000.csv.zip"


async def download_bhavcopy(trade_date: dt.date | None = None) -> NseBhavCopyReportModel:
    """Download the Bhavcopy ZIP for *trade_date* (defaults to today IST).

    Returns the ORM model instance that was upserted into the DB.
    Raises on unrecoverable errors (caller should catch and log).
    """
    if trade_date is None:
        trade_date = dt.datetime.now(IST).date()

    STORE_DIR.mkdir(parents=True, exist_ok=True)
    file_name = _file_name(trade_date)
    dest = STORE_DIR / file_name
    date_dmy = trade_date.strftime("%d-%m-%Y")       # for NSE API  e.g. 19-06-2026
    date_nodash = trade_date.strftime("%Y%m%d")       # for archives URL

    logger.info("NSE Bhavcopy download starting for %s", trade_date)

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=60) as client:
        # Step 1 — establish NSE session cookies
        try:
            await client.get(NSE_HOME)
        except Exception:
            logger.warning("Could not reach NSE homepage; proceeding without session cookies")

        # Step 2 — resolve download URL via NSE API
        download_url: str | None = None
        try:
            api_url = NSE_REPORTS_API.format(date=date_dmy)
            resp = await client.get(api_url)
            if resp.status_code == 200:
                data = resp.json()
                # API returns a list; first item has the link
                if isinstance(data, list) and data:
                    download_url = data[0].get("link") or data[0].get("url")
                elif isinstance(data, dict):
                    download_url = data.get("link") or data.get("url")
        except Exception as exc:
            logger.warning("NSE reports API failed (%s); falling back to archives URL", exc)

        # Step 3 — fallback to direct archives URL
        if not download_url:
            download_url = NSE_ARCHIVES_URL.format(date_nodash=date_nodash)
            logger.info("Using archives fallback URL: %s", download_url)

        # Step 4 — stream download
        try:
            async with client.stream("GET", download_url) as stream:
                stream.raise_for_status()
                with open(dest, "wb") as fh:
                    async for chunk in stream.aiter_bytes(chunk_size=65536):
                        fh.write(chunk)
        except Exception as exc:
            _upsert_record(
                trade_date, file_name, str(dest),
                status="failed", error=str(exc),
            )
            raise

    file_size = dest.stat().st_size
    logger.info("Downloaded %s (%d bytes)", file_name, file_size)
    return _upsert_record(
        trade_date, file_name, str(dest),
        file_size=file_size, status="downloaded",
    )


def _upsert_record(
    trade_date: dt.date,
    file_name: str,
    file_path: str,
    *,
    file_size: int | None = None,
    status: str = "downloaded",
    error: str | None = None,
) -> NseBhavCopyReportModel:
    """Insert or update the DB row for *trade_date* (unique constraint keeps one row per day)."""
    from sqlalchemy import select

    factory = NseSessionLocal()
    db: Session = factory()
    try:
        existing = db.scalar(
            select(NseBhavCopyReportModel).where(
                NseBhavCopyReportModel.file_date == trade_date
            )
        )
        now_utc = dt.datetime.now(dt.timezone.utc)
        if existing:
            existing.file_name = file_name
            existing.file_path = file_path
            existing.file_size_bytes = file_size
            existing.downloaded_at = now_utc if status == "downloaded" else existing.downloaded_at
            existing.status = status
            existing.error_message = error
            record = existing
        else:
            record = NseBhavCopyReportModel(
                id=uuid.uuid4(),
                file_date=trade_date,
                file_name=file_name,
                file_path=file_path,
                file_size_bytes=file_size,
                downloaded_at=now_utc if status == "downloaded" else None,
                status=status,
                error_message=error,
            )
            db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Backfill — catch up on any dates missed while the server was down
# ---------------------------------------------------------------------------

# Weekdays only; NSE doesn't publish on Sat/Sun. Public holidays still
# produce a "failed" record (no file on NSE) which is fine — it shows intent.
_BACKFILL_DAYS = 7


def _trading_dates(n: int) -> list[dt.date]:
    """Return the last *n* weekday dates up to and including today IST."""
    today = dt.datetime.now(IST).date()
    dates: list[dt.date] = []
    d = today
    while len(dates) < n:
        if d.weekday() < 5:  # Mon–Fri
            dates.append(d)
        d -= dt.timedelta(days=1)
    return dates


async def backfill_missing() -> int:
    """Download Bhavcopy for any of the last N trading days that aren't in the DB.

    Returns the number of dates attempted.
    """
    from sqlalchemy import select as sa_select

    factory = NseSessionLocal()
    db: Session = factory()
    try:
        dates = _trading_dates(_BACKFILL_DAYS)
        existing = set(
            db.scalars(
                sa_select(NseBhavCopyReportModel.file_date).where(
                    NseBhavCopyReportModel.file_date.in_(dates),
                    NseBhavCopyReportModel.status == "downloaded",
                )
            ).all()
        )
    finally:
        db.close()

    missing = [d for d in dates if d not in existing]
    if not missing:
        logger.info("NSE Bhavcopy backfill: all %d recent trading days present", len(dates))
        return 0

    logger.info("NSE Bhavcopy backfill: %d missing dates → %s", len(missing), missing)
    for trade_date in sorted(missing):
        try:
            await download_bhavcopy(trade_date)
        except Exception as exc:
            logger.error("Backfill download failed for %s: %s", trade_date, exc)
        await asyncio.sleep(2)  # be polite to NSE
    return len(missing)


# ---------------------------------------------------------------------------
# Scheduler — runs inside FastAPI lifespan as a background asyncio task
# ---------------------------------------------------------------------------

async def _scheduler_loop() -> None:
    """On startup, backfill missing dates. Then fire download every day at 20:00 IST."""
    logger.info("NSE Bhavcopy scheduler started")

    # ── Startup backfill ──────────────────────────────────────────────
    try:
        filled = await backfill_missing()
        if filled:
            logger.info("NSE Bhavcopy backfill completed (%d dates attempted)", filled)
    except Exception as exc:
        logger.error("NSE Bhavcopy backfill error: %s", exc)

    # ── Daily 20:00 IST loop ──────────────────────────────────────────
    while True:
        now_ist = dt.datetime.now(IST)
        # Next 20:00 IST
        target = now_ist.replace(hour=20, minute=0, second=0, microsecond=0)
        if now_ist >= target:
            target += dt.timedelta(days=1)
        wait_seconds = (target - now_ist).total_seconds()
        logger.info(
            "NSE Bhavcopy: next download in %.0f seconds (at %s IST)",
            wait_seconds,
            target.strftime("%Y-%m-%d %H:%M"),
        )
        await asyncio.sleep(wait_seconds)

        trade_date = dt.datetime.now(IST).date()
        try:
            await download_bhavcopy(trade_date)
            # Auto-ingest prices and run daily valuation after download
            await _post_download_valuation(trade_date)
        except Exception as exc:
            logger.error("NSE Bhavcopy download failed for %s: %s", trade_date, exc)
        # Small buffer before recalculating next trigger
        await asyncio.sleep(5)


async def _post_download_valuation(trade_date: dt.date) -> None:
    """After a bhavcopy download, parse prices and run mark-to-market."""
    from app.core.database import SessionLocal
    from app.services.market_data import parse_bhavcopy_zip, upsert_prices, run_daily_valuation

    # Find the ZIP path
    from sqlalchemy import select as sa_select
    factory = NseSessionLocal()
    nse_db = factory()
    try:
        report = nse_db.scalar(
            sa_select(NseBhavCopyReportModel).where(
                NseBhavCopyReportModel.file_date == trade_date,
                NseBhavCopyReportModel.status == "downloaded",
            )
        )
    finally:
        nse_db.close()

    if report is None:
        logger.warning("No bhavcopy record for %s after download — skipping valuation", trade_date)
        return

    db = SessionLocal()
    try:
        rows = parse_bhavcopy_zip(report.file_path)
        if rows:
            upsert_prices(db, trade_date, rows)
            run_daily_valuation(db, trade_date)
            db.commit()
            logger.info("Post-download valuation complete for %s", trade_date)
    except Exception as exc:
        db.rollback()
        logger.error("Post-download valuation failed for %s: %s", trade_date, exc)
    finally:
        db.close()


def start_scheduler() -> asyncio.Task:
    """Schedule the background download loop. Call from FastAPI lifespan."""
    return asyncio.create_task(_scheduler_loop())
