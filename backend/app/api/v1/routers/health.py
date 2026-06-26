"""Liveness / readiness probes + seed helpers."""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
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


@router.post("/seed-demo")
def seed_demo_data(db: Session = Depends(get_db)) -> dict:
    """Insert sample onboarding applications for demo purposes. Idempotent."""
    from app.core.security import encrypt_pii, hash_pan
    from app.infrastructure.db.models_onboarding import OnboardingApplicationModel

    s = get_settings()
    if s.environment == "production":
        return {"status": "disabled in production"}

    existing = db.scalar(
        select(func.count()).select_from(OnboardingApplicationModel)
    ) or 0
    if existing >= 5:
        return {"status": "skipped", "reason": f"{existing} applications already exist"}

    now = dt.datetime.now(dt.UTC)

    demo_applicants = [
        {
            "full_name": "Rajesh Kumar Sharma",
            "email": "rajesh.sharma@example.com",
            "mobile": "+919876543210",
            "pan": "ABCPS1234K",
            "investor_type": "individual",
            "proposed_investment_paise": 5000000_00,
            "status": "under_review",
            "risk_category": "moderate",
            "risk_score": 55,
            "created_at": now - dt.timedelta(days=2),
        },
        {
            "full_name": "Priya Mehta",
            "email": "priya.mehta@example.com",
            "mobile": "+919876543211",
            "pan": "BCDPM5678L",
            "investor_type": "individual",
            "proposed_investment_paise": 10000000_00,
            "status": "active",
            "risk_category": "aggressive",
            "risk_score": 78,
            "created_at": now - dt.timedelta(days=10),
        },
        {
            "full_name": "Vikram Singh Rathore",
            "email": "vikram.rathore@example.com",
            "mobile": "+919876543212",
            "pan": "CDEVR9012M",
            "investor_type": "individual",
            "proposed_investment_paise": 7500000_00,
            "status": "under_review",
            "risk_category": "conservative",
            "risk_score": 32,
            "created_at": now - dt.timedelta(days=1),
        },
        {
            "full_name": "Ananya Desai",
            "email": "ananya.desai@example.com",
            "mobile": "+919876543213",
            "pan": "DEFAD3456N",
            "investor_type": "individual",
            "proposed_investment_paise": 20000000_00,
            "status": "active",
            "risk_category": "moderate",
            "risk_score": 60,
            "created_at": now - dt.timedelta(days=15),
        },
        {
            "full_name": "Siddharth Patel",
            "email": "siddharth.patel@example.com",
            "mobile": "+919876543214",
            "pan": "EFGSP7890P",
            "investor_type": "individual",
            "proposed_investment_paise": 6000000_00,
            "status": "rejected",
            "risk_category": None,
            "risk_score": None,
            "rejection_reason": "KYC verification failed - PAN mismatch",
            "created_at": now - dt.timedelta(days=5),
        },
        {
            "full_name": "Meera Joshi",
            "email": "meera.joshi@example.com",
            "mobile": "+919876543215",
            "pan": "FGHMJ2345Q",
            "investor_type": "individual",
            "proposed_investment_paise": 15000000_00,
            "status": "under_review",
            "risk_category": "aggressive",
            "risk_score": 82,
            "created_at": now - dt.timedelta(hours=6),
        },
        {
            "full_name": "Arjun Kapoor Industries LLP",
            "email": "arjun.kapoor@akillp.com",
            "mobile": "+919876543216",
            "pan": "GHIAK6789R",
            "investor_type": "corporate",
            "proposed_investment_paise": 50000000_00,
            "status": "active",
            "risk_category": "moderate",
            "risk_score": 50,
            "created_at": now - dt.timedelta(days=30),
        },
        {
            "full_name": "Neha Agarwal",
            "email": "neha.agarwal@example.com",
            "mobile": "+919876543217",
            "pan": "HIJNA1234S",
            "investor_type": "individual",
            "proposed_investment_paise": 8000000_00,
            "status": "kyc_rejected",
            "risk_category": None,
            "risk_score": None,
            "rejection_reason": "Aadhaar details could not be verified",
            "created_at": now - dt.timedelta(days=3),
        },
    ]

    inserted = 0
    for d in demo_applicants:
        pan_h = hash_pan(d["pan"])
        exists = db.scalar(
            select(func.count())
            .select_from(OnboardingApplicationModel)
            .where(OnboardingApplicationModel.pan_hash == pan_h)
        )
        if exists:
            continue

        try:
            pan_encrypted = encrypt_pii(d["pan"])
        except RuntimeError:
            pan_encrypted = "DEMO_ENCRYPTED_" + d["pan"]

        app = OnboardingApplicationModel(
            id=uuid.uuid4(),
            status=d["status"],
            investor_type=d["investor_type"],
            full_name=d["full_name"],
            email=d["email"],
            mobile=d["mobile"],
            pan_hash=pan_h,
            pan_enc=pan_encrypted,
            proposed_investment_paise=d["proposed_investment_paise"],
            risk_category=d.get("risk_category"),
            risk_score=d.get("risk_score"),
            rejection_reason=d.get("rejection_reason"),
            created_at=d["created_at"],
            updated_at=now,
        )
        db.add(app)
        inserted += 1

    db.commit()
    return {"status": "ok", "inserted": inserted}
