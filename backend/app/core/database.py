"""SQLAlchemy engine, session factory, and declarative base."""
from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    """Lazily create the engine on first use (not at import time)."""
    s = get_settings()
    return create_engine(
        s.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=s.debug,
    )


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a session; auto-commit only when the session has pending changes.

    This avoids issuing a pointless COMMIT on read-only requests while still
    committing writes made via flush() in route handlers.
    """
    factory = get_session_factory()
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
