"""NSE CM-UDiFF Common Bhavcopy daily reports endpoints.

Accessible to investors and all staff.
Admin/staff also get a manual trigger endpoint.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.api import dependencies as deps
from app.infrastructure.db.nse_database import get_nse_db
from app.infrastructure.db.models_nse_reports import NseBhavCopyReportModel

router = APIRouter(prefix="/nse-reports", tags=["nse-reports"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BhavCopyRecord(BaseModel):
    id: str
    file_date: dt.date
    file_name: str
    file_size_bytes: int | None = None
    downloaded_at: dt.datetime | None = None
    status: str
    error_message: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, m: NseBhavCopyReportModel) -> "BhavCopyRecord":
        return cls(
            id=str(m.id),
            file_date=m.file_date,
            file_name=m.file_name,
            file_size_bytes=m.file_size_bytes,
            downloaded_at=m.downloaded_at,
            status=m.status,
            error_message=m.error_message,
        )


class BhavCopyListResponse(BaseModel):
    records: list[BhavCopyRecord]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=BhavCopyListResponse)
def list_reports(
    days: int = Query(default=7, ge=1, le=90, description="How many calendar days back to show"),
    db: Session = Depends(get_nse_db),
    _user: dict = Depends(deps.get_current_user),
):
    """Return the last *days* calendar days of Bhavcopy records (newest first)."""
    since = dt.date.today() - dt.timedelta(days=days - 1)
    rows = db.scalars(
        select(NseBhavCopyReportModel)
        .where(NseBhavCopyReportModel.file_date >= since)
        .order_by(desc(NseBhavCopyReportModel.file_date))
    ).all()
    return BhavCopyListResponse(
        records=[BhavCopyRecord.from_orm_model(r) for r in rows],
        total=len(rows),
    )


@router.get("/all", response_model=BhavCopyListResponse)
def list_all_reports(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_nse_db),
    _user: dict = Depends(deps.get_current_user),
):
    """Paginated full history."""
    rows = db.scalars(
        select(NseBhavCopyReportModel)
        .order_by(desc(NseBhavCopyReportModel.file_date))
        .limit(limit)
        .offset(offset)
    ).all()
    from sqlalchemy import func

    total = db.scalar(
        select(func.count()).select_from(NseBhavCopyReportModel)
) or 0
    return BhavCopyListResponse(
        records=[BhavCopyRecord.from_orm_model(r) for r in rows],
        total=total,
    )


@router.get("/download/{file_date}")
def download_file(
    file_date: dt.date,
    db: Session = Depends(get_nse_db),
    _user: dict = Depends(deps.get_current_user),
):
    """Stream the ZIP file for the given trading date."""
    record = db.scalar(
        select(NseBhavCopyReportModel).where(
            NseBhavCopyReportModel.file_date == file_date
        )
    )
    if not record:
        raise HTTPException(404, f"No Bhavcopy record found for {file_date}")
    if record.status != "downloaded":
        raise HTTPException(409, f"File for {file_date} is not ready (status: {record.status})")
    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk — may have been moved")
    return FileResponse(
        path=str(file_path),
        media_type="application/zip",
        filename=record.file_name,
    )


@router.post("/trigger", status_code=202)
async def trigger_download(
    file_date: dt.date | None = None,
    _user: dict = Depends(deps.require_staff),
):
    """Manually trigger a Bhavcopy download (staff only). Runs in the background."""
    import asyncio
    from app.services.nse_bhavcopy import download_bhavcopy

    target = file_date or dt.date.today()
    asyncio.create_task(download_bhavcopy(target))
    return {"message": f"Download triggered for {target}", "date": str(target)}
