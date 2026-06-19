"""Auth endpoints — JWT token issuance.

In production this would be backed by a real identity provider (Keycloak, Auth0).
For dev/demo, this issues tokens directly given a username and role.
"""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    role: str = "investor"  # investor | relationship_manager | compliance


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
def issue_token(body: LoginRequest):
    """Dev-only endpoint — issue a JWT for the given username/role.
    Disabled in production environments."""
    if get_settings().environment not in ("local", "development", "test"):
        raise HTTPException(status_code=404, detail="Not found")
    token = create_access_token(sub=body.username, role=body.role)
    return TokenResponse(access_token=token)


# ── Email + password registration / login ───────────────────────────────────
import uuid  # noqa: E402
import secrets  # noqa: E402
import logging  # noqa: E402
import datetime as _dtmod  # noqa: E402
from fastapi import Depends  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.security import (  # noqa: E402
    hash_password,
    verify_password,
    generate_verification_token,
    hash_token,
)
from app.api.v1.dependencies import get_current_user  # noqa: E402
from app.infrastructure.db.models_auth import (  # noqa: E402
    UserModel,
    EmailVerificationTokenModel,
    PhoneVerificationCodeModel,
)
from app.infrastructure.external.email_client import get_email_sender  # noqa: E402
from app.infrastructure.external.sms_client import get_sms_sender  # noqa: E402


def _now():
    return _dtmod.datetime.now(_dtmod.timezone.utc)

_ROLE_ALIASES = {"rm": "relationship_manager"}
_VALID_ROLES = ("investor", "relationship_manager", "compliance")


def _expires_in() -> int:
    return get_settings().jwt_expiry_minutes * 60


def _issue_email_verification(db: Session, user: UserModel) -> None:
    """Create a fresh email-verification token and send the link."""
    # Invalidate any outstanding tokens for this user.
    for t in db.scalars(
        select(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.user_id == user.id,
            EmailVerificationTokenModel.is_used.is_(False),
        )
    ).all():
        t.is_used = True

    raw = generate_verification_token()
    db.add(EmailVerificationTokenModel(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=_now() + _dtmod.timedelta(hours=48),
        created_at=_now(),
    ))
    db.flush()

    link = f"{get_settings().app_base_url.rstrip('/')}/verify-email?token={raw}"
    get_email_sender().send(
        to=user.email,
        subject="Verify your Aurum PMS email",
        body=(
            f"Hi {user.full_name},\n\n"
            f"Please verify your email address by opening this link:\n{link}\n\n"
            f"This link expires in 48 hours. If you didn't create an account, ignore this email."
        ),
    )


def _issue_phone_otp(db: Session, user: UserModel, phone: str) -> None:
    """Create a 6-digit OTP for the phone and send it."""
    for c in db.scalars(
        select(PhoneVerificationCodeModel).where(
            PhoneVerificationCodeModel.user_id == user.id,
            PhoneVerificationCodeModel.is_used.is_(False),
        )
    ).all():
        c.is_used = True

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(PhoneVerificationCodeModel(
        id=uuid.uuid4(),
        user_id=user.id,
        phone=phone,
        code_hash=hash_token(code),
        expires_at=_now() + _dtmod.timedelta(minutes=get_settings().otp_ttl_minutes),
        created_at=_now(),
    ))
    db.flush()
    get_sms_sender().send_otp(phone=phone, code=code)


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "investor"
    phone: str | None = None


class RegisterResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 1800


class LoginCredentials(BaseModel):
    email: str
    password: str


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    email_verified: bool
    phone: str | None = None
    phone_verified: bool = False
    created_at: _dtmod.datetime
    last_login_at: _dtmod.datetime | None = None

    model_config = {"from_attributes": True}


class PhoneRequest(BaseModel):
    phone: str | None = None


class VerifyPhoneRequest(BaseModel):
    code: str


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    role = _ROLE_ALIASES.get(body.role, body.role)
    if role not in _VALID_ROLES:
        raise HTTPException(status_code=422, detail="Invalid role")
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    email = body.email.strip().lower()
    existing = db.query(UserModel).filter_by(email=email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    phone = (body.phone or "").strip() or None
    user = UserModel(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role=role,
        is_active=True,
        email_verified=False,
        phone=phone,
        phone_verified=False,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(user)
    db.flush()

    # Fire off verifications. Don't fail the signup if a provider hiccups.
    try:
        _issue_email_verification(db, user)
    except Exception:  # noqa: BLE001
        logging.getLogger("pms.auth").exception("Failed to send verification email")
    if phone:
        try:
            _issue_phone_otp(db, user, phone)
        except Exception:  # noqa: BLE001
            logging.getLogger("pms.auth").exception("Failed to send phone OTP")

    token = create_access_token(sub=email, role=role)
    return RegisterResponse(access_token=token, expires_in=_expires_in())


@router.post("/login", response_model=RegisterResponse)
def login(body: LoginCredentials, db: Session = Depends(get_db)):
    """Authenticate against the users table (email + password)."""
    email = body.email.strip().lower()
    user = db.query(UserModel).filter_by(email=email).first()
    # Same response for unknown email vs. wrong password (no user enumeration).
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    user.last_login_at = _now()
    db.flush()
    token = create_access_token(sub=user.email, role=user.role)
    return RegisterResponse(access_token=token, expires_in=_expires_in())


@router.get("/me", response_model=UserProfileResponse)
def me(current=Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the authenticated user's profile (from the JWT subject)."""
    record = db.query(UserModel).filter_by(email=current.get("sub", "").lower()).first()
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    return record


def _current_user_record(db: Session, current: dict) -> UserModel:
    record = db.query(UserModel).filter_by(email=current.get("sub", "").lower()).first()
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    return record


class MessageResponse(BaseModel):
    message: str


@router.post("/send-phone-otp", response_model=MessageResponse)
def send_phone_otp(
    body: PhoneRequest,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send (or resend) a phone OTP to the logged-in user's number."""
    user = _current_user_record(db, current)
    phone = (body.phone or user.phone or "").strip()
    if not phone:
        raise HTTPException(status_code=422, detail="No phone number on file — provide one")
    user.phone = phone
    if user.phone_verified and phone == user.phone:
        user.phone_verified = False  # number being (re)confirmed
    _issue_phone_otp(db, user, phone)
    return MessageResponse(message="A verification code has been sent to your phone.")


@router.post("/verify-phone", response_model=MessageResponse)
def verify_phone(
    body: VerifyPhoneRequest,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify the most recent phone OTP for the logged-in user."""
    user = _current_user_record(db, current)
    record = db.scalars(
        select(PhoneVerificationCodeModel)
        .where(
            PhoneVerificationCodeModel.user_id == user.id,
            PhoneVerificationCodeModel.is_used.is_(False),
        )
        .order_by(PhoneVerificationCodeModel.created_at.desc())
    ).first()

    if record is None:
        raise HTTPException(status_code=400, detail="No active code — request a new one")
    if record.expires_at < _now():
        raise HTTPException(status_code=400, detail="Code has expired — request a new one")
    if record.attempts >= 5:
        record.is_used = True
        raise HTTPException(status_code=429, detail="Too many attempts — request a new code")

    if hash_token(body.code.strip()) != record.code_hash:
        record.attempts += 1
        raise HTTPException(status_code=400, detail="Incorrect code")

    record.is_used = True
    user.phone = record.phone
    user.phone_verified = True
    user.updated_at = _now()
    return MessageResponse(message="Phone number verified.")
