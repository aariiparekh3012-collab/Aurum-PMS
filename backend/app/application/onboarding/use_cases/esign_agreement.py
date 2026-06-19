"""Use case: Aadhaar eSign for the PMS agreement.

Flow:
1. initiate() → returns transaction_id
2. User redirected to eSign ASP (NSDL/UIDAI)
3. After signing, eSign ASP calls our webhook (handle_esign_callback)
4. confirm() → polls for signed document (for direct integration)
"""
from __future__ import annotations

import uuid

import structlog

from app.application.onboarding.dto import ApplicationView
from app.application.onboarding.mappers import to_view
from app.application.onboarding.ports import EsignPort, EventPublisher
from app.core.exceptions import ExternalServiceError, NotFoundError
from app.domain.onboarding.repositories import OnboardingRepository

log = structlog.get_logger(__name__)


class EsignAgreementUseCase:
    def __init__(
        self, repo: OnboardingRepository, esign: EsignPort, publisher: EventPublisher
    ) -> None:
        self._repo = repo
        self._esign = esign
        self._publisher = publisher

    def initiate(
        self, application_id: uuid.UUID, document_bytes: bytes | None = None
    ) -> str:
        """Initiate Aadhaar eSign.

        Args:
            application_id: Application UUID
            document_bytes: PMS agreement PDF (optional, uses default if None)

        Returns:
            Transaction ID for tracking
        """
        app = self._repo.get(application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")

        # Generate PMS agreement if document_bytes not provided
        if document_bytes is None:
            document_bytes = self._generate_pms_agreement(app)

        log.info("esign_initiate_uc", application_id=str(application_id))

        transaction_id = self._esign.initiate(
            application_id=str(application_id), document_bytes=document_bytes
        )
        return transaction_id

    def confirm(self, application_id: uuid.UUID, transaction_id: str) -> ApplicationView:
        """Confirm eSign completion (polling method).

        Args:
            application_id: Application UUID
            transaction_id: Transaction ID from initiate()

        Returns:
            Updated application view
        """
        app = self._repo.get(application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")

        log.info(
            "esign_confirm_uc",
            application_id=str(application_id),
            transaction_id=transaction_id,
        )

        result = self._esign.fetch_result(transaction_id=transaction_id)
        if not result.signed:
            raise ExternalServiceError(
                "eSign not completed", code="esign_not_signed"
            )

        app.mark_agreement_signed(esign_reference=result.reference)
        self._repo.update(app)
        self._publisher.publish(app.pull_events())

        log.info(
            "esign_agreement_signed",
            application_id=str(application_id),
            esign_reference=result.reference,
        )
        return to_view(app)

    def handle_esign_callback(
        self, application_id: uuid.UUID, payload: dict
    ) -> ApplicationView:
        """Handle webhook callback from eSign ASP after signing.

        Args:
            application_id: Application UUID
            payload: Callback payload from eSign ASP
                    { transaction_id, status, esign_reference, signed_document_url }

        Returns:
            Updated application view
        """
        app = self._repo.get(application_id)
        if app is None:
            raise NotFoundError("Onboarding application not found")

        status = payload.get("status", "").upper()
        transaction_id = payload.get("transaction_id")
        esign_reference = payload.get("esign_reference")
        log.info(
            "esign_callback_received",
            application_id=str(application_id),
            transaction_id=transaction_id,
            status=status,
        )

        if status == "SIGNED" and esign_reference:
            app.mark_agreement_signed(esign_reference=esign_reference)
            self._repo.update(app)
            self._publisher.publish(app.pull_events())

            log.info(
                "esign_agreement_signed_via_callback",
                application_id=str(application_id),
                esign_reference=esign_reference,
            )
        elif status == "REJECTED":
            log.warning(
                "esign_rejected",
                application_id=str(application_id),
                transaction_id=transaction_id,
            )
        else:
            log.warning(
                "esign_callback_unknown_status",
                application_id=str(application_id),
                status=status,
            )

        return to_view(app)

    @staticmethod
    def _generate_pms_agreement(app) -> bytes:
        """Generate PMS agreement PDF from template.

        This is a placeholder that returns a minimal PDF.
        In production, use a PDF generation library (e.g., ReportLab, Jinja2 + weasyprint)
        """
        # Minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< >>
stream
BT
/F1 12 Tf
50 700 Td
(Aurum PMS - Portfolio Management Agreement) Tj
0 -30 Td
(Client: """ + app.full_name.encode() + b""") Tj
0 -30 Td
(PAN: """ + app.pan.value.encode() + b""") Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
400
%%EOF"""
        return pdf_content
