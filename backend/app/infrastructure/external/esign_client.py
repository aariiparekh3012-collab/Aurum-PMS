"""Digio eSign adapter implementing EsignPort.

Uses Digio's REST API for Aadhaar-based eSign.
Docs: https://documentation.digio.in/digisign/

Auth: Basic Auth (client_id:client_secret)
Sandbox base: https://ext.digio.in
Production base: https://api.digio.in
"""
from __future__ import annotations

import base64
import uuid

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.application.onboarding.ports import EsignPort, EsignResult
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

log = structlog.get_logger(__name__)


class DigioEsignAdapter(EsignPort):
    """Digio Aadhaar eSign integration via REST API."""

    def __init__(self) -> None:
        s = get_settings()
        if not s.digio_client_id or not s.digio_client_secret:
            raise RuntimeError(
                "DIGIO_CLIENT_ID and DIGIO_CLIENT_SECRET required for live eSign"
            )
        self._base = (s.digio_base_url or "https://ext.digio.in").rstrip("/")
        # Digio uses HTTP Basic Auth
        credentials = f"{s.digio_client_id}:{s.digio_client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._auth_header = f"Basic {encoded}"
        self._timeout = 30

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=6),
        reraise=True,
    )
    def initiate(self, *, application_id: str, document_bytes: bytes) -> str:
        """Upload document to Digio and create an eSign request.

        Returns the Digio document ID (e.g., DIDxxx...) as the transaction_id.
        """
        request_id = str(uuid.uuid4())
        log.info(
            "digio_esign_initiate",
            application_id=application_id,
            doc_size=len(document_bytes),
            request_id=request_id,
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                # Step 1: Upload document and create sign request
                resp = client.post(
                    f"{self._base}/v2/client/document/upload",
                    headers={
                        "Authorization": self._auth_header,
                    },
                    files={
                        "file": (
                            f"agreement_{application_id}.pdf",
                            document_bytes,
                            "application/pdf",
                        ),
                    },
                    data={
                        "signers": '[{"identifier": "self", "sign_type": "aadhaar"}]',
                        "file_name": f"PMS Agreement - {application_id}",
                        "notify_signers": "true",
                        "send_sign_link": "true",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPStatusError as e:
            log.error(
                "digio_esign_initiate_error",
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            raise ExternalServiceError(
                f"Digio eSign initiation failed: HTTP {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            log.error("digio_esign_initiate_network_error", error=str(e))
            raise ExternalServiceError(
                f"Digio eSign network error: {e}"
            ) from e

        document_id = data.get("id", "")
        if not document_id:
            raise ExternalServiceError(
                f"Digio returned no document ID: {data}"
            )

        log.info("digio_esign_initiated", document_id=document_id)
        return document_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
    )
    def fetch_result(self, *, transaction_id: str) -> EsignResult:
        """Check the signing status of a Digio document."""
        log.info("digio_esign_status_check", document_id=transaction_id)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(
                    f"{self._base}/v2/client/document/{transaction_id}",
                    headers={"Authorization": self._auth_header},
                )
                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPStatusError as e:
            log.error(
                "digio_esign_status_error",
                status=e.response.status_code,
                body=e.response.text[:500],
            )
            raise ExternalServiceError(
                f"Digio status check failed: HTTP {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            log.error("digio_esign_status_network_error", error=str(e))
            raise ExternalServiceError(
                f"Digio status check network error: {e}"
            ) from e

        # Digio document statuses: requested, partially_signed, signed, expired, cancelled
        doc_status = (data.get("agreement_status") or "").lower()
        signed = doc_status == "signed"
        signed_url = data.get("signing_url") or data.get("download_url")

        log.info(
            "digio_esign_status_result",
            document_id=transaction_id,
            status=doc_status,
            signed=signed,
        )

        return EsignResult(
            signed=signed,
            reference=transaction_id,
            signed_document_url=signed_url if signed else None,
        )


# Backward compat alias
AadhaarEsignAdapter = DigioEsignAdapter


class FakeEsignAdapter(EsignPort):
    """Always-pass adapter for local dev and tests."""

    def initiate(self, *, application_id: str, document_bytes: bytes) -> str:
        return f"FAKE-ESIGN-{uuid.uuid4().hex[:8]}"

    def fetch_result(self, *, transaction_id: str) -> EsignResult:
        return EsignResult(
            signed=True,
            reference=transaction_id,
            signed_document_url=f"https://fake-storage.example.com/{transaction_id}.pdf",
        )
