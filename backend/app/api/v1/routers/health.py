"""Liveness / readiness probes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(tags=["health"])
logger = logging.getLogger("pms.health")


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


@router.get("/test-email")
def test_email() -> dict:
    """Dev-only: send a test email to verify SMTP config works."""
    s = get_settings()
    if s.environment == "production":
        return {"status": "disabled in production"}

    from app.infrastructure.external.email_client import get_email_sender

    sender = get_email_sender()
    sender_type = type(sender).__name__

    try:
        sender.send(
            to=s.smtp_user or "test@example.com",
            subject="Aurum PMS - SMTP Test",
            body="If you see this email, your SMTP configuration is working correctly!",
        )
        return {
            "status": "sent",
            "sender_type": sender_type,
            "smtp_host": s.smtp_host,
            "smtp_user": s.smtp_user,
            "to": s.smtp_user,
        }
    except Exception as exc:
        logger.exception("Test email failed")
        return {
            "status": "failed",
            "sender_type": sender_type,
            "smtp_host": s.smtp_host,
            "error": str(exc),
        }
