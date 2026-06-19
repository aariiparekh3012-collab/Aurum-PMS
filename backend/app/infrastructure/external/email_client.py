"""Email senders.

Follows the same provider-or-fake pattern as the KYC/bank/e-sign adapters:
``get_email_sender()`` returns a real SMTP sender when SMTP is configured,
otherwise a console sender that logs the message (so the flow is fully testable
in dev without any external service).
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger("pms.email")


class EmailSender(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    """Dev sender — logs the email instead of delivering it."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        logger.warning(
            "[DEV EMAIL] (no SMTP configured) ->\n  To: %s\n  Subject: %s\n  %s",
            to, subject, body,
        )


class SmtpEmailSender:
    """Real sender over SMTP (Gmail, Outlook, company server, etc.)."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        s = get_settings()
        msg = EmailMessage()
        msg["From"] = s.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            if s.smtp_use_tls:
                server.starttls()
            if s.smtp_user:
                server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
        logger.info("Sent email to %s (subject=%r)", to, subject)


def get_email_sender() -> EmailSender:
    """Real SMTP sender if smtp_host is configured, else the dev console sender."""
    return SmtpEmailSender() if get_settings().smtp_host else ConsoleEmailSender()
