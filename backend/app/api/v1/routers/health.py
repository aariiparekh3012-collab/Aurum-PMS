"""Liveness / readiness probes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
def liveness() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readiness(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))

    result: dict = {"status": "ready", "db": "ok"}

    # Check Redis if configured
    s = get_settings()
    if s.redis_url:
        try:
            from app.infrastructure.external.redis_message_bus import RedisMessageBus
            bus = RedisMessageBus()
            result["redis"] = "ok" if bus.health_check() else "unhealthy"
        except Exception:
            result["redis"] = "unreachable"

    return result
