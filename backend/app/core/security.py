"""Security utilities — PII encryption, PAN hashing, JWT tokens."""
from __future__ import annotations

import hashlib
import secrets as _secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().effective_fernet_key
    if not key:
        raise RuntimeError("No encryption key configured (set FERNET_KEY or PII_ENCRYPTION_KEY)")
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def hash_pan(pan: str) -> str:
    """HMAC-SHA256 of uppercased PAN keyed on the server secret.

    Plain SHA-256 is unsafe here because the PAN keyspace is small
    (~3 billion values: AAAAA0000A–ZZZZZ9999Z) and trivially brute-forced.
    Using HMAC with a secret key makes offline rainbow tables infeasible.
    """
    import hmac as _hmac
    secret = get_settings().jwt_secret.encode()
    return _hmac.new(secret, pan.upper().encode(), hashlib.sha256).hexdigest()


def create_access_token(*, sub: str, role: str, extra: dict | None = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub, "role": role, "iat": now,
        "exp": now + timedelta(minutes=s.jwt_expiry_minutes),
        **(extra or {}),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])


# ── PII aliases + auth helpers (used by clients/investor/auth_recovery) ──────

def encrypt_pii(plaintext: str) -> str:
    return encrypt(plaintext)


def decrypt_pii(ciphertext: str) -> str:
    return decrypt(ciphertext)


def generate_verification_token() -> str:
    """Opaque URL-safe token (emailed to the user; only its hash is stored)."""
    return _secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Deterministic hash for storing verification / reset tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 password hash (stdlib only). Format: pbkdf2$<salt>$<hex>."""
    salt = _secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return _secrets.compare_digest(dk.hex(), expected)
