"""Centralised application settings loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False,
        extra="ignore",
    )

    # ── App
    app_name: str = "PMS Onboarding"
    environment: str = "local"
    debug: bool = False
    allowed_origins: str = "http://localhost:5173"
    api_v1_prefix: str = "/api/v1"

    # ── Database
    database_url: str = "postgresql://pms:pms@localhost:5432/pms"

    # ── NSE Reports Database (separate DB for daily Bhavcopy downloads)
    nse_database_url: str = "postgresql://postgres:aarya123@localhost:5432/downloaddailyreport"

    # ── Auth / JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    jwt_access_ttl_minutes: int = 30

    # ── PII encryption
    fernet_key: str = ""
    pii_encryption_key: str = ""

    # ── SEBI business rules
    min_investment_inr: int = 5_000_000

    # ── External services (legacy — kept for backward compat)
    bank_verify_base_url: str = ""
    bank_verify_api_key: str = ""
    kyc_base_url: str = ""
    kra_base_url: str = ""
    kyc_api_key: str = ""
    kra_api_key: str = ""
    ckyc_base_url: str = ""
    ckyc_api_key: str = ""
    esign_base_url: str = ""
    esign_api_key: str = ""

    # ── Surepass (KYC + bank verification)
    surepass_base_url: str = "https://kyc-api.surepass.io/api/v1"
    surepass_api_token: str = ""

    # ── Digio (eSign)
    digio_base_url: str = "https://ext.digio.in"
    digio_client_id: str = ""
    digio_client_secret: str = ""

    # ── Redis
    redis_url: str = ""

    # ── Public app URL (used to build verification links in emails)
    app_base_url: str = "http://localhost:5173"

    # ── Email (SMTP). If smtp_host is blank, a dev console sender is used
    #    (the email body is logged instead of actually sent).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Aurum PMS <no-reply@aurumpms.com>"
    smtp_use_tls: bool = True

    # ── SMS / OTP (MSG91). If msg91_auth_key is blank, a dev console sender
    #    is used (the OTP is logged instead of texted).
    msg91_auth_key: str = ""
    msg91_sender_id: str = "AURUMP"
    msg91_route: str = "4"
    otp_ttl_minutes: int = 10

    @property
    def effective_fernet_key(self) -> str:
        return self.fernet_key or self.pii_encryption_key

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    def validate_production(self) -> None:
        """Guard against running production with insecure defaults."""
        if self.environment != "production":
            return
        if "change" in self.jwt_secret.lower() or len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET is insecure — set a strong secret for production")
        if not self.effective_fernet_key:
            raise RuntimeError("PII_ENCRYPTION_KEY must be set in production")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_production()
    return s
