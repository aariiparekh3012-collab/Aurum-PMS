"""SQLAlchemy ORM model for daily security prices (from NSE bhavcopy)."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SecurityPriceModel(Base):
    __tablename__ = "security_prices"
    __table_args__ = (
        Index(
            "ix_security_prices_sec_date",
            "security_id", "price_date",
            unique=True,
        ),
        {"schema": "reference"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference.securities_master.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
