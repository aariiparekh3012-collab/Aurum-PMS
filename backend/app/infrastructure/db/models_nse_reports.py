"""SQLAlchemy ORM model for NSE CM-UDiFF Common Bhavcopy daily reports.

Each row = one day's downloaded ZIP file.
- file_date: the trading date the file covers (unique — no overwrites)
- file_name: original NSE filename
- file_path: absolute path on disk where the ZIP is stored
- file_size_bytes: size in bytes
- downloaded_at: when the scheduler grabbed it
- status: 'pending' | 'downloaded' | 'failed'
- error_message: populated on failure
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.nse_database import NseBase


class NseBhavCopyReportModel(NseBase):
    __tablename__ = "nse_bhavcopy_reports"
    __table_args__ = (
        Index("ix_nse_bhavcopy_file_date", "file_date", unique=True),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_date: Mapped[dt.date] = mapped_column(Date, nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    downloaded_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
