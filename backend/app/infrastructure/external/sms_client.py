"""SMS / OTP senders.

Provider-or-fake pattern: ``get_sms_sender()`` returns a real MSG91 sender when
an MSG91 auth key is configured, otherwise a console sender that logs the OTP
(so phone verification is fully testable in dev without sending real texts).
"""
from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger("pms.sms")


class SmsSender(Protocol):
    def send_otp(self, *, phone: str, code: str) -> None: ...


class ConsoleSmsSender:
    """Dev sender — logs the OTP instead of texting it."""

    def send_otp(self, *, phone: str, code: str) -> None:
        logger.warning(
            "[DEV SMS] (no MSG91 configured) -> %s : your Aurum PMS code is %s",
            phone, code,
        )


class Msg91SmsSender:
    """Real sender via MSG91's flow/SMS API (India)."""

    def send_otp(self, *, phone: str, code: str) -> None:
        s = get_settings()
        # MSG91 expects numbers without a leading '+'.
        number = phone.lstrip("+")
        payload = {
            "sender": s.msg91_sender_id,
            "route": s.msg91_route,
            "country": "91",
            "sms": [{
                "message": f"Your Aurum PMS verification code is {code}. It expires in {s.otp_ttl_minutes} minutes.",
                "to": [number],
            }],
        }
        headers = {"authkey": s.msg91_auth_key, "content-type": "application/json"}
        resp = httpx.post(
            "https://api.msg91.com/api/v2/sendsms",
            json=payload, headers=headers, timeout=15,
        )
        resp.raise_for_status()
        logger.info("Sent OTP SMS to %s via MSG91", number)


def get_sms_sender() -> SmsSender:
    """Real MSG91 sender if an auth key is configured, else the dev console sender."""
    return Msg91SmsSender() if get_settings().msg91_auth_key else ConsoleSmsSender()
