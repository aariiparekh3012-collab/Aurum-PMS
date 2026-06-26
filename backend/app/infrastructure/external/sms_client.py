"""OTP / message senders -- WhatsApp Cloud API (preferred) -> MSG91 -> dev console.

Provider-or-fake pattern: ``get_sms_sender()`` picks the best available sender
based on configuration.  Priority:

1. **WhatsApp Business Cloud API** (Meta) -- free tier: 1,000 service
   conversations/month.  Sends OTP via a pre-approved authentication template
   message.  Requires WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN.
2. **MSG91** -- paid Indian SMS gateway (DLT-compliant).
3. **Console** -- logs to stdout (dev mode, no real messages sent).
"""
from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger("pms.sms")


class SmsSender(Protocol):
    def send_otp(self, *, phone: str, code: str) -> None: ...
    def send(self, *, to: str, message: str, template_id: str | None = None) -> None: ...


# -- Dev console sender -------------------------------------------------------

class ConsoleSmsSender:
    """Dev sender -- logs messages instead of delivering."""

    def send_otp(self, *, phone: str, code: str) -> None:
        logger.warning(
            "[DEV SMS] (no provider configured) -> %s : your Aurum PMS code is %s",
            phone, code,
        )

    def send(self, *, to: str, message: str, template_id: str | None = None) -> None:
        logger.warning(
            "[DEV SMS] (no provider configured) ->\n"
            "  To: %s\n  Template: %s\n  %s",
            to, template_id or "none", message[:300],
        )


# -- WhatsApp Business Cloud API sender ---------------------------------------

class WhatsAppCloudSender:
    """Send OTP and notifications via Meta WhatsApp Business Cloud API.

    Setup checklist (one-time, free):
    1. Create a Meta Business account at business.facebook.com
    2. Add WhatsApp product in Meta Developer portal
    3. Register your phone number (9769795975) as the sender
    4. Create an "authentication" message template for OTP
       (Meta auto-approves auth templates within minutes)
    5. Generate a permanent System User access token with permissions:
       whatsapp_business_messaging, whatsapp_business_management
    6. Set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN in .env

    Free tier: 1,000 service conversations/month (plenty for demo/prototype).
    """

    API_BASE = "https://graph.facebook.com/v21.0"

    def __init__(self) -> None:
        s = get_settings()
        self._phone_number_id = s.whatsapp_phone_number_id
        self._token = s.whatsapp_access_token
        self._otp_template = s.whatsapp_otp_template_name
        self._otp_ttl = s.otp_ttl_minutes

    def _url(self) -> str:
        return f"{self.API_BASE}/{self._phone_number_id}/messages"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def send_otp(self, *, phone: str, code: str) -> None:
        """Send OTP via WhatsApp authentication template.

        Uses the authentication template with a one-tap / copy-code button.
        If no auth template is configured, falls back to a plain text message.
        """
        number = _normalize_phone_whatsapp(phone)

        if self._otp_template:
            # Authentication template with OTP button (Meta-approved)
            payload = {
                "messaging_product": "whatsapp",
                "to": number,
                "type": "template",
                "template": {
                    "name": self._otp_template,
                    "language": {"code": "en"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": code},
                            ],
                        },
                        {
                            "type": "button",
                            "sub_type": "url",
                            "index": "0",
                            "parameters": [
                                {"type": "text", "text": code},
                            ],
                        },
                    ],
                },
            }
        else:
            # Plain text (only works within 24h service window)
            payload = {
                "messaging_product": "whatsapp",
                "to": number,
                "type": "text",
                "text": {
                    "body": (
                        f"Your Aurum PMS verification code is: {code}\n"
                        f"It expires in {self._otp_ttl} minutes.\n"
                        f"Do not share this code with anyone."
                    ),
                },
            }

        resp = httpx.post(self._url(), json=payload, headers=self._headers(), timeout=15)

        if resp.status_code not in (200, 201):
            logger.error(
                "WhatsApp API error %d: %s", resp.status_code, resp.text[:300],
            )
            raise RuntimeError(f"WhatsApp API returned {resp.status_code}: {resp.text[:200]}")

        logger.info("OTP sent via WhatsApp to %s", number)

    def send(self, *, to: str, message: str, template_id: str | None = None) -> None:
        """Send a transactional notification via WhatsApp text message."""
        number = _normalize_phone_whatsapp(to)
        payload = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "text",
            "text": {"body": message},
        }
        resp = httpx.post(self._url(), json=payload, headers=self._headers(), timeout=15)
        if resp.status_code not in (200, 201):
            logger.error(
                "WhatsApp API error %d: %s", resp.status_code, resp.text[:300],
            )
            raise RuntimeError(f"WhatsApp API returned {resp.status_code}")
        logger.info("WhatsApp message sent to %s", number)


# -- MSG91 sender (fallback for SMS) ------------------------------------------

class Msg91SmsSender:
    """Real sender via MSG91 -- OTP + transactional notifications (India, DLT-compliant)."""

    SEND_SMS_URL = "https://api.msg91.com/api/v2/sendsms"
    FLOW_URL = "https://control.msg91.com/api/v5/flow/"

    def __init__(self) -> None:
        s = get_settings()
        self._auth_key = s.msg91_auth_key
        self._sender_id = s.msg91_sender_id
        self._route = s.msg91_route
        self._default_template = s.msg91_template_id
        self._otp_ttl = s.otp_ttl_minutes

    def send_otp(self, *, phone: str, code: str) -> None:
        number = _normalize_phone(phone)
        payload = {
            "sender": self._sender_id,
            "route": self._route,
            "country": "91",
            "sms": [{
                "message": (
                    f"Your Aurum PMS verification code is {code}. "
                    f"It expires in {self._otp_ttl} minutes."
                ),
                "to": [number],
            }],
        }
        resp = httpx.post(
            self.SEND_SMS_URL,
            json=payload,
            headers={"authkey": self._auth_key, "content-type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("Sent OTP SMS to %s via MSG91", number)

    def send(self, *, to: str, message: str, template_id: str | None = None) -> None:
        phone = _normalize_phone(to)
        tid = template_id or self._default_template
        if tid:
            payload = {
                "template_id": tid,
                "short_url": "0",
                "recipients": [{"mobiles": phone, "message": message}],
            }
            resp = httpx.post(
                self.FLOW_URL,
                json=payload,
                headers={"authkey": self._auth_key, "Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code not in (200, 201):
                logger.error("MSG91 flow error %d: %s", resp.status_code, resp.text[:300])
                raise RuntimeError(f"MSG91 flow returned {resp.status_code}")
            logger.info("SMS sent via MSG91 flow to %s (template=%s)", phone, tid)
        else:
            payload = {
                "sender": self._sender_id,
                "route": self._route,
                "country": "91",
                "sms": [{"message": message, "to": [phone]}],
            }
            resp = httpx.post(
                self.SEND_SMS_URL,
                json=payload,
                headers={"authkey": self._auth_key, "content-type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            logger.info("SMS sent via MSG91 direct to %s", phone)


# -- Helpers -------------------------------------------------------------------

def _normalize_phone_whatsapp(phone: str) -> str:
    """Normalize to WhatsApp format: country code + number, digits only (e.g. 919876543210)."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return "91" + digits  # default India
    if digits.startswith("0") and len(digits) == 11:
        return "91" + digits[1:]
    return digits


def _normalize_phone(phone: str) -> str:
    """Ensure phone has country code for MSG91 (default India 91)."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return "91" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "91" + digits[1:]
    return digits.lstrip("+")


# -- Factory -------------------------------------------------------------------

_sender: SmsSender | None = None


def get_sms_sender() -> SmsSender:
    """Pick the best available sender:
    1. WhatsApp Cloud API (if WHATSAPP_ACCESS_TOKEN configured)
    2. MSG91 (if MSG91_AUTH_KEY configured)
    3. Console logger (dev)
    """
    global _sender
    if _sender is not None:
        return _sender

    s = get_settings()
    if s.whatsapp_access_token and s.whatsapp_phone_number_id:
        _sender = WhatsAppCloudSender()
        logger.info("OTP sender: WhatsApp Cloud API (phone_number_id=%s)", s.whatsapp_phone_number_id)
    elif s.msg91_auth_key:
        _sender = Msg91SmsSender()
        logger.info("OTP sender: MSG91")
    else:
        _sender = ConsoleSmsSender()
        logger.info("OTP sender: Console (dev mode)")
    return _sender
