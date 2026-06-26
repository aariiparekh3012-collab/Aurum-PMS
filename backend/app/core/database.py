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


def SessionLocal() -> Session:
    """Convenience: create a standalone session (for background tasks)."""
    return get_session_factory()()


def get_db() -> Generator[Session, None, None]:
    """Yield a session and always commit on success.

    An empty COMMIT is essentially free, and the previous ``db.new or
    db.dirty`` guard silently skipped commits after flush() — objects move
    out of db.new once flushed, so the condition was False even when the
    transaction held uncommitted writes.
    """
    factory = get_session_factory()
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
