"""Email senders — SendGrid (preferred) → SMTP fallback → dev console.

Follows the provider-or-fake pattern: ``get_email_sender()`` picks the best
available sender based on configuration. All senders support HTML bodies.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger("pms.email")


class EmailSender(Protocol):
    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> None: ...


# ── Dev console sender ─────────────────────────────────────────────────────

class ConsoleEmailSender:
    """Dev sender — logs the email instead of delivering it."""

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> None:
        logger.warning(
            "[DEV EMAIL] (no email provider configured) ->\n"
            "  To: %s\n  Subject: %s\n  %s",
            to, subject, body[:500],
        )


# ── SendGrid sender ───────────────────────────────────────────────────────

class SendGridEmailSender:
    """Transactional email via SendGrid v3 Mail Send API."""

    API_URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self) -> None:
        s = get_settings()
        self._api_key = s.sendgrid_api_key
        self._from_email = s.sendgrid_from_email
        self._from_name = s.sendgrid_from_name

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> None:
        content = [{"type": "text/plain", "value": body}]
        if html:
            content.append({"type": "text/html", "value": html})

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self._from_email, "name": self._from_name},
            "subject": subject,
            "content": content,
        }

        resp = httpx.post(
            self.API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )

        if resp.status_code not in (200, 201, 202):
            logger.error(
                "SendGrid error %d: %s", resp.status_code, resp.text[:300],
            )
            raise RuntimeError(f"SendGrid returned {resp.status_code}")

        logger.info("Email sent via SendGrid to %s (subject=%r)", to, subject)


# ── SMTP sender ────────────────────────────────────────────────────────────

class SmtpEmailSender:
    """Real sender over SMTP (Gmail, Outlook, company server, etc.)."""

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> None:
        s = get_settings()
        msg = EmailMessage()
        msg["From"] = s.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")

        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            if s.smtp_use_tls:
                server.starttls()
            if s.smtp_user:
                server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
        logger.info("Email sent via SMTP to %s (subject=%r)", to, subject)


# ── Factory ────────────────────────────────────────────────────────────────

_sender: EmailSender | None = None


def get_email_sender() -> EmailSender:
    """Pick the best available email sender:
    1. SendGrid (if API key configured)
    2. SMTP (if smtp_host configured)
    3. Console logger (dev)
    """
    global _sender
    if _sender is not None:
        return _sender

    s = get_settings()
    if s.sendgrid_api_key:
        _sender = SendGridEmailSender()
        logger.info("Email sender: SendGrid")
    elif s.smtp_host:
        _sender = SmtpEmailSender()
        logger.info("Email sender: SMTP (%s)", s.smtp_host)
    else:
        _sender = ConsoleEmailSender()
        logger.info("Email sender: Console (dev mode)")
    return _sender
