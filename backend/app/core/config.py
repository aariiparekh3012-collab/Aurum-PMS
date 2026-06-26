"""Centralised application settings loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False,
        extra="ignore",
    )

    # -- App
    app_name: str = "PMS Onboarding"
    environment: str = "local"
    debug: bool = False
    allowed_origins: str = "http://localhost:5173"
    api_v1_prefix: str = "/api/v1"

    # -- Database
    database_url: str = "postgresql://postgres:aarya123@localhost:5432/aurumpms"

    # -- NSE Reports Database (separate DB for daily Bhavcopy downloads)
    nse_database_url: str = "postgresql://postgres:aarya123@localhost:5432/downloaddailyreport"

    # -- Auth / JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # -- PII encryption
    fernet_key: str = ""
    pii_encryption_key: str = ""

    # -- SEBI business rules
    min_investment_inr: int = 5_000_000

    # -- Surepass (KYC + bank verification)
    surepass_base_url: str = "https://kyc-api.surepass.io/api/v1"
    surepass_api_token: str = ""

    # -- Digio (eSign)
    digio_base_url: str = "https://ext.digio.in"
    digio_client_id: str = ""
    digio_client_secret: str = ""

    # -- Redis
    redis_url: str = ""

    # -- Public app URL (used to build verification links in emails)
    app_base_url: str = "http://localhost:5173"

    # -- Email (SMTP). If smtp_host is blank, a dev console sender is used.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Aurum PMS <no-reply@aurumpms.com>"
    smtp_use_tls: bool = True

    # -- Document storage
    document_storage_backend: str = "local"  # "local" or "s3"
    document_storage_path: str = ""  # local path; defaults to project/document_uploads
    document_s3_bucket: str = "pms-documents"
    document_s3_endpoint: str = ""  # MinIO endpoint, leave blank for AWS
    document_s3_access_key: str = ""
    document_s3_secret_key: str = ""
    document_s3_region: str = "ap-south-1"

    # -- SendGrid (transactional email). If blank, falls back to SMTP or console.
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "no-reply@aurumpms.com"
    sendgrid_from_name: str = "Aurum PMS"

    # -- WhatsApp Cloud API (OTP + notifications). Free: 1000 conversations/month.
    whatsapp_phone_number_id: str = ""  # from Meta Developer portal
    whatsapp_access_token: str = ""     # System User permanent token
    whatsapp_otp_template_name: str = "aurum_otp"  # your approved auth template name

    # -- SMS / OTP via MSG91 (fallback if WhatsApp not configured)
    msg91_auth_key: str = ""
    msg91_sender_id: str = "AURUMP"
    msg91_route: str = "4"
    msg91_template_id: str = ""
    otp_ttl_minutes: int = 10

    # -- Mock OTP (demo/dev only - delete these in production)
    mock_otp_phones: str = ""
    mock_otp_code: str = ""

    @property
    def mock_otp_phone_set(self) -> set[str]:
        """Normalized set of test phone numbers that accept the hardcoded OTP."""
        if not self.mock_otp_phones:
            return set()
        return {p.strip().lstrip("+") for p in self.mock_otp_phones.split(",") if p.strip()}

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
            raise RuntimeError("JWT_SECRET is insecure - set a strong secret for production")
        if not self.effective_fernet_key:
            raise RuntimeError("PII_ENCRYPTION_KEY must be set in production")
        if "localdev123" in self.database_url or "localdev123" in self.nse_database_url:
            raise RuntimeError("Database URLs still contain default dev password - set real credentials")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_production()
    return s
