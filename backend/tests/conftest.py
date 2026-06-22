"""Shared test fixtures — DB session, TestClient, auth helpers.

Requires a PostgreSQL database for API tests (provided by docker-compose or CI).
Tests that don't request DB fixtures (e.g. pure domain tests) run without Postgres.
"""
from __future__ import annotations

import os

# Set test env BEFORE any app imports so get_settings() picks them up.
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long-enough")
os.environ.setdefault("FERNET_KEY", "dGVzdC1rZXktMzItYnl0ZXMtdXJsLXNhZmU=")
os.environ.setdefault("NSE_DATABASE_URL", "postgresql://pms:pms@localhost:5432/pms_test")

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

# Clear caches so test env vars are used even if another module triggered them.
from app.core.config import get_settings

get_settings.cache_clear()

from app.core.database import Base, get_db, get_engine  # noqa: E402

get_engine.cache_clear()

from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402

# Schemas used by the multi-schema model layout.
_PG_SCHEMAS = ("client", "trading", "portfolio", "reference", "notifications", "performance")


# ── Database fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def _ensure_tables():
    """Create all PG schemas + ORM tables once per pytest session.

    Only triggered by tests that request ``db_session`` or ``client``.
    """
    engine = get_engine()
    with engine.connect() as conn:
        for schema in _PG_SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    with engine.connect() as conn:
        for schema in reversed(_PG_SCHEMAS):
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        conn.commit()


@pytest.fixture
def db_session(_ensure_tables) -> Generator[Session, None, None]:
    """Yield a DB session wrapped in a transaction that rolls back after the test.

    This gives each test a clean database without the overhead of re-creating tables.
    """
    engine = get_engine()
    conn = engine.connect()
    txn = conn.begin()
    session = Session(bind=conn, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        txn.rollback()
        conn.close()


# ── TestClient ───────────────────────────────────────────────────────────

@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with the DB session overridden and NSE scheduler mocked."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Mock the NSE Bhavcopy scheduler so the lifespan doesn't need the NSE DB.
    mock_task = AsyncMock()
    with patch("app.services.nse_bhavcopy.start_scheduler", return_value=mock_task):
        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc

    app.dependency_overrides.clear()


# ── Auth helpers ─────────────────────────────────────────────────────────

@pytest.fixture
def investor_token() -> str:
    return create_access_token(sub="test-investor@example.com", role="investor")


@pytest.fixture
def compliance_token() -> str:
    return create_access_token(sub="compliance@example.com", role="compliance")


@pytest.fixture
def rm_token() -> str:
    return create_access_token(sub="rm@example.com", role="relationship_manager")


def auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header dict from a JWT string."""
    return {"Authorization": f"Bearer {token}"}
