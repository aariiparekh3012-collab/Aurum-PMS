"""Password reset + email verification endpoints.

Separated from main auth router for clarity. These are low-frequency,
security-sensitive operations with rate limiting considerations.
"""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import DomainError
from app.core.security import (
    generate_verification_token,
    hash_password,
    hash_token,
)
from app.infrastructure.external.email_client import get_email_sender
from app.infrastructure.db.models_auth import (
    EmailVerificationTokenModel,
    PasswordResetTokenModel,
    UserModel,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    message: str


# ── Password Reset ────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset link. Always returns success to prevent email enumeration."""
    now = dt.datetime.now(dt.timezone.utc)

    user = db.scalars(
        select(UserModel).where(UserModel.email == body.email)
    ).first()

    if user:
        # Invalidate any existing unused reset tokens
        existing = db.scalars(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.user_id == user.id,
                PasswordResetTokenModel.is_used.is_(False),
            )
        ).all()
        for t in existing:
            t.is_used = True

        # Create new token (24h expiry)
        raw_token = generate_verification_token()
        reset_token = PasswordResetTokenModel(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + dt.timedelta(hours=24),
            created_at=now,
        )
        db.add(reset_token)
        db.flush()

        link = f"{get_settings().app_base_url.rstrip('/')}/reset-password?token={raw_token}"
        try:
            get_email_sender().send(
                to=user.email,
                subject="Reset your Aurum PMS password",
                body=(
                    f"Hi {user.full_name},\n\n"
                    f"Reset your password using this link:\n{link}\n\n"
                    f"This link expires in 24 hours. If you didn't request this, ignore this email."
                ),
            )
        except Exception:  # noqa: BLE001
            pass  # never reveal send failures on this endpoint

    # Always return success to prevent email enumeration
    return MessageResponse(message="If an account exists with that email, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid token."""
    now = dt.datetime.now(dt.timezone.utc)
    token_hash = hash_token(body.token)

    token_record = db.scalars(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash
        )
    ).first()

    if not token_record:
        raise DomainError("Invalid or expired reset token", code="bad_request")

    if token_record.is_used:
        raise DomainError("This reset link has already been used", code="bad_request")

    if token_record.expires_at < now:
        raise DomainError("Reset link has expired", code="bad_request")

    # Update password
    user = db.get(UserModel, token_record.user_id)
    if not user:
        raise DomainError("User not found", code="not_found")

    user.password_hash = hash_password(body.new_password)
    user.updated_at = now
    token_record.is_used = True

    # Revoke all refresh tokens (force re-login on all devices)
    from app.infrastructure.db.models_auth import RefreshTokenModel
    db.execute(
        update(RefreshTokenModel)
        .where(RefreshTokenModel.user_id == user.id)
        .values(is_revoked=True)
    )

    return MessageResponse(message="Password has been reset. Please log in with your new password.")


# ── Email Verification ────────────────────────────────────────────────────

@router.post("/verify-email", response_model=MessageResponse)
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email address using a valid token."""
    now = dt.datetime.now(dt.timezone.utc)
    token_hash = hash_token(body.token)

    token_record = db.scalars(
        select(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.token_hash == token_hash
        )
    ).first()

    if not token_record:
        raise DomainError("Invalid verification token", code="bad_request")

    if token_record.is_used:
        return MessageResponse(message="Email already verified.")

    if token_record.expires_at < now:
        raise DomainError("Verification link has expired", code="bad_request")

    user = db.get(UserModel, token_record.user_id)
    if not user:
        raise DomainError("User not found", code="not_found")

    user.email_verified = True
    user.updated_at = now
    token_record.is_used = True

    return MessageResponse(message="Email verified successfully.")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Resend email verification token."""
    now = dt.datetime.now(dt.timezone.utc)

    user = db.scalars(
        select(UserModel).where(UserModel.email == body.email)
    ).first()

    if user and not user.email_verified:
        # Invalidate existing
        existing = db.scalars(
            select(EmailVerificationTokenModel).where(
                EmailVerificationTokenModel.user_id == user.id,
                EmailVerificationTokenModel.is_used.is_(False),
            )
        ).all()
        for t in existing:
            t.is_used = True

        raw_token = generate_verification_token()
        verification = EmailVerificationTokenModel(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + dt.timedelta(hours=48),
            created_at=now,
        )
        db.add(verification)
        db.flush()

        link = f"{get_settings().app_base_url.rstrip('/')}/verify-email?token={raw_token}"
        try:
            get_email_sender().send(
                to=user.email,
                subject="Verify your Aurum PMS email",
                body=(
                    f"Hi {user.full_name},\n\n"
                    f"Please verify your email address by opening this link:\n{link}\n\n"
                    f"This link expires in 48 hours."
                ),
            )
        except Exception:  # noqa: BLE001
            pass

    return MessageResponse(message="If the email is registered and unverified, a verification link has been sent.")
