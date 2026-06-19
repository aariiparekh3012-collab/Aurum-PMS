"""Surepass KYC adapter implementing KycPort.

Uses Surepass PAN Verification API to verify identity.
Docs: https://surepass.io/pan-verification-api-1/

Auth: Bearer token
Endpoint: POST {base_url}/pan/pan
"""
from __future__ import annotations

import uuid

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.application.onboarding.ports import KycPort, KycResult
from app.core.config import get_settings
from app.core.exceptions import ValidationError

log = structlog.get_logger(__name__)


class SurepassKycAdapter(KycPort):
    """Surepass PAN verification — calls the Surepass sandbox/prod API."""

    def __init__(self) -> None:
        s = get_settings()
        if not s.surepass_base_url or not s.surepass_api_token:
            raise RuntimeError(
                "SUREPASS_BASE_URL and SUREPASS_API_TOKEN required for live KYC"
            )
        self._base = s.surepass_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {s.surepass_api_token}",
            "Content-Type": "application/json",
        }
        self._timeout = 15

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=6),
        reraise=True,
    )
    def verify(self, *, pan: str, aadhaar_last4: str, name: str) -> KycResult:
        if not self._is_valid_pan(pan):
            raise ValidationError("Invalid PAN format", code="invalid_pan")
        if not aadhaar_last4.isdigit() or len(aadhaar_last4) != 4:
            raise ValidationError(
                "Aadhaar last4 must be 4 digits", code="invalid_aadhaar"
            )

        request_id = str(uuid.uuid4())
        log.info("surepass_pan_verify_start", pan=pan[:5] + "***", request_id=request_id)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._base}/pan/pan",
                    headers={**self._headers, "X-Request-ID": request_id},
                    json={"id_number": pan},
                )
                resp.raise_for_status()
                body = resp.json()

        except httpx.HTTPStatusError as e:
            log.error(
                "surepass_pan_verify_http_error",
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            if 400 <= e.response.status_code < 500:
                return KycResult(
                    verified=False,
                    source="surepass",
                    reference="",
                    reason=f"Verification rejected: {e.response.text[:200]}",
                )
            raise

        except httpx.RequestError as e:
            log.error("surepass_pan_verify_network_error", error=str(e))
            raise

        # Surepass response shape:
        # {"data": {"pan_number": "...", "full_name": "...", "category": "...", ...},
        #  "status_code": 200, "success": true, "message_code": "success"}
        data = body.get("data", {})
        success = body.get("success", False)
        pan_status = data.get("status", "").upper() if data else ""
        verified = success and pan_status in ("VALID", "VERIFIED", "")

        # Name cross-check (basic fuzzy)
        api_name = (data.get("full_name") or "").upper().strip()
        input_name = name.upper().strip()
        if verified and api_name and input_name not in api_name and api_name not in input_name:
            # Names don't match — still mark verified but note mismatch
            log.warning(
                "surepass_name_mismatch",
                api_name=api_name,
                input_name=input_name,
            )

        reference = data.get("pan_number", pan)
        log.info(
            "surepass_pan_verify_done",
            verified=verified,
            reference=reference,
        )

        return KycResult(
            verified=verified,
            source="surepass",
            reference=reference,
            reason=body.get("message") if not verified else None,
        )

    @staticmethod
    def _is_valid_pan(pan: str) -> bool:
        return (
            len(pan) == 10
            and pan[0:5].isalpha()
            and pan[5:9].isdigit()
            and pan[9].isalpha()
        )


# Backward compat alias
KraKycAdapter = SurepassKycAdapter


class FakeKycAdapter(KycPort):
    """Deterministic stub for local dev / tests: PAN ending in 'Z' fails."""

    def verify(self, *, pan: str, aadhaar_last4: str, name: str) -> KycResult:
        if pan.endswith("Z"):
            return KycResult(False, "kra", "", reason="Name/PAN mismatch (stub)")
        return KycResult(True, "kra", f"KRA-{pan[-4:]}-{aadhaar_last4}")
