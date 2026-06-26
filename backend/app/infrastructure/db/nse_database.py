"""Separate SQLAlchemy engine + session for the NSE downloaddailyreport database.

All NSE Bhavcopy models and services import from here instead of app.core.database,
so they hit the downloaddailyreport database rather than the main pms database.
"""
from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class NseBase(DeclarativeBase):
    pass


@lru_cache
def get_nse_engine() -> Engine:
    s = get_settings()
    return create_engine(
        s.nse_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=s.debug,
    )


def ensure_nse_tables() -> None:
    """Auto-create NseBase tables if they don't exist (no Alembic for this DB)."""
    from app.infrastructure.db.models_nse_reports import NseBhavCopyReportModel  # noqa: F401
    NseBase.metadata.create_all(bind=get_nse_engine())


def get_nse_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_nse_engine(), autoflush=False, expire_on_commit=False)


# Used by the downloader service (called outside FastAPI request context)
NseSessionLocal = get_nse_session_factory


def get_nse_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a session to downloaddailyreport."""
    factory = get_nse_session_factory()
    db = factory()
    try:
        yield db
        if db.new or db.dirty or db.deleted:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
