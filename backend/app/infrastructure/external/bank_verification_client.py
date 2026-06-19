"""Surepass penny-drop bank verification adapter implementing BankVerificationPort.

Uses Surepass Bank Account Verification (penny drop) API.
Docs: https://surepass.io/penny-drop-api/

Auth: Bearer token
Endpoint: POST {base_url}/bank-verification/
"""
from __future__ import annotations

import uuid
from difflib import SequenceMatcher

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.application.onboarding.ports import BankVerificationPort, BankVerificationResult
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

log = structlog.get_logger(__name__)


class SurepassPennyDropAdapter(BankVerificationPort):
    """Surepass penny-drop bank account verification."""

    def __init__(self) -> None:
        s = get_settings()
        if not s.surepass_base_url or not s.surepass_api_token:
            raise RuntimeError(
                "SUREPASS_BASE_URL and SUREPASS_API_TOKEN required for live bank verification"
            )
        self._base = s.surepass_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {s.surepass_api_token}",
            "Content-Type": "application/json",
        }
        self._timeout = 30  # penny-drop can be slower

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=6),
        reraise=True,
    )
    def verify(
        self, *, account_number: str, ifsc: str, name: str
    ) -> BankVerificationResult:
        request_id = str(uuid.uuid4())
        log.info(
            "surepass_bank_verify_start",
            ifsc=ifsc,
            acct_last4=account_number[-4:] if len(account_number) >= 4 else "****",
            request_id=request_id,
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._base}/bank-verification/",
                    headers={**self._headers, "X-Request-ID": request_id},
                    json={
                        "id_number": account_number,
                        "ifsc": ifsc,
                        "ifsc_details": True,
                    },
                )
                resp.raise_for_status()
                body = resp.json()

        except httpx.HTTPStatusError as e:
            log.error(
                "surepass_bank_verify_http_error",
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            if 400 <= e.response.status_code < 500:
                return BankVerificationResult(
                    verified=False,
                    name_match_score=0.0,
                    reason=f"Bank verification rejected: {e.response.text[:200]}",
                )
            raise ExternalServiceError(
                f"Surepass bank verification failed: HTTP {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            log.error("surepass_bank_verify_network_error", error=str(e))
            raise ExternalServiceError(
                f"Surepass bank verification network error: {e}"
            ) from e

        # Response: {"data": {"account_exists": true, "full_name": "...",
        #            "utr": "...", "amount_deposited": ...}, "success": true, ...}
        data = body.get("data", {})
        success = body.get("success", False)
        account_exists = data.get("account_exists", False)
        verified = success and account_exists

        # Compute name match score
        bank_name = (data.get("full_name") or data.get("name_at_bank") or "").upper().strip()
        input_name = name.upper().strip()
        name_match_score = (
            SequenceMatcher(None, input_name, bank_name).ratio() if bank_name else 0.0
        )

        reason = None
        if not verified:
            reason = data.get("message") or body.get("message") or "Account not verified"

        log.info(
            "surepass_bank_verify_done",
            verified=verified,
            name_match_score=round(name_match_score, 2),
        )

        return BankVerificationResult(
            verified=verified,
            name_match_score=round(name_match_score, 2),
            reason=reason,
        )


# Backward compat alias
PennyDropAdapter = SurepassPennyDropAdapter


class FakeBankVerificationAdapter(BankVerificationPort):
    """Always-pass adapter for local dev and tests."""

    def verify(
        self, *, account_number: str, ifsc: str, name: str
    ) -> BankVerificationResult:
        return BankVerificationResult(verified=True, name_match_score=0.97)
