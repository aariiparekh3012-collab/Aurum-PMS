"""Notification dispatcher — sends email + SMS for key app events.

Covers two event categories:
  1. Onboarding status changes (KYC verified, approved, rejected, etc.)
  2. Trade confirmations (order filled, allocation complete)

Each event fires both an email (HTML) and an SMS to the relevant user.
In dev mode (no providers configured), messages are logged to console.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from app.infrastructure.external.email_client import get_email_sender
from app.infrastructure.external.sms_client import get_sms_sender

logger = logging.getLogger("pms.notifications")


# ── Data classes for notification payloads ─────────────────────────────────

@dataclass
class OnboardingEvent:
    """Payload for onboarding status change notifications."""
    applicant_name: str
    email: str
    phone: str
    status: str
    application_id: str
    proposed_investment_inr: float = 0
    rejection_reason: str | None = None


@dataclass
class TradeEvent:
    """Payload for trade execution notifications."""
    client_name: str
    email: str
    phone: str
    account_code: str
    security_symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    price_inr: float
    trade_date: date
    order_id: str | None = None


# ── Dispatcher ─────────────────────────────────────────────────────────────

def notify_onboarding_status(event: OnboardingEvent) -> None:
    """Send email + SMS for an onboarding status change."""
    subject, body_text, body_html = _build_onboarding_content(event)

    try:
        email_sender = get_email_sender()
        email_sender.send(
            to=event.email,
            subject=subject,
            body=body_text,
            html=body_html,
        )
    except Exception as exc:
        logger.error("Failed to send onboarding email to %s: %s", event.email, exc)

    if event.phone:
        sms_text = _build_onboarding_sms(event)
        try:
            sms_sender = get_sms_sender()
            sms_sender.send(to=event.phone, message=sms_text)
        except Exception as exc:
            logger.error("Failed to send onboarding SMS to %s: %s", event.phone, exc)


def notify_trade_confirmation(event: TradeEvent) -> None:
    """Send email + SMS for a trade execution."""
    subject, body_text, body_html = _build_trade_content(event)

    try:
        email_sender = get_email_sender()
        email_sender.send(
            to=event.email,
            subject=subject,
            body=body_text,
            html=body_html,
        )
    except Exception as exc:
        logger.error("Failed to send trade email to %s: %s", event.email, exc)

    if event.phone:
        sms_text = _build_trade_sms(event)
        try:
            sms_sender = get_sms_sender()
            sms_sender.send(to=event.phone, message=sms_text)
        except Exception as exc:
            logger.error("Failed to send trade SMS to %s: %s", event.phone, exc)


# ── Content builders — Onboarding ──────────────────────────────────────────

_STATUS_MESSAGES: dict[str, tuple[str, str]] = {
    "kyc_pending": (
        "KYC Verification In Progress",
        "Your KYC verification is now in progress. We'll notify you once it's complete.",
    ),
    "kyc_verified": (
        "KYC Verification Successful",
        "Great news! Your KYC verification has been completed successfully. "
        "Please proceed with the next steps in your onboarding.",
    ),
    "kyc_rejected": (
        "KYC Verification — Action Required",
        "Unfortunately, your KYC verification could not be completed. "
        "Please review the details and resubmit the required documents.",
    ),
    "risk_profiled": (
        "Risk Profile Assessed",
        "Your risk profile has been assessed. You can now proceed to the agreement step.",
    ),
    "agreement_pending": (
        "PMS Agreement — Awaiting Signature",
        "Your PMS agreement is ready for e-signature. Please complete it to proceed.",
    ),
    "agreement_signed": (
        "PMS Agreement Signed",
        "Thank you for signing the PMS agreement. "
        "Your application has been submitted for compliance review.",
    ),
    "under_review": (
        "Application Under Review",
        "Your application is now being reviewed by our compliance team. "
        "We'll notify you once a decision is made.",
    ),
    "active": (
        "Welcome to Aurum PMS!",
        "Congratulations! Your PMS account has been activated. "
        "You can now log in to your investor portal to view your portfolio.",
    ),
    "rejected": (
        "Application Update",
        "We regret to inform you that your application could not be approved at this time.",
    ),
}


def _build_onboarding_content(event: OnboardingEvent) -> tuple[str, str, str]:
    """Return (subject, plain_text, html) for an onboarding status email."""
    title, message = _STATUS_MESSAGES.get(
        event.status,
        ("Application Status Update", f"Your application status has been updated to: {event.status}."),
    )

    subject = f"Aurum PMS — {title}"

    if event.status == "kyc_rejected" and event.rejection_reason:
        message += f"\n\nReason: {event.rejection_reason}"
    if event.status == "rejected" and event.rejection_reason:
        message += f"\n\nReason: {event.rejection_reason}"

    body_text = (
        f"Dear {event.applicant_name},\n\n"
        f"{message}\n\n"
        f"Application ID: {event.application_id[:8]}\n\n"
        "If you have any questions, please contact your relationship manager.\n\n"
        "Best regards,\nAurum PMS"
    )

    body_html = _wrap_html_template(
        title=title,
        greeting=f"Dear {event.applicant_name},",
        body=f"<p>{message.replace(chr(10), '<br>')}</p>"
             f'<p style="color:#888;font-size:13px;">Application ID: {event.application_id[:8]}</p>',
        footer="If you have any questions, please contact your relationship manager.",
    )

    return subject, body_text, body_html


def _build_onboarding_sms(event: OnboardingEvent) -> str:
    """Short SMS text for onboarding status change."""
    title, _ = _STATUS_MESSAGES.get(
        event.status,
        ("Status Update", ""),
    )
    return (
        f"Aurum PMS: {title}. "
        f"Hi {event.applicant_name.split()[0]}, your application ({event.application_id[:8]}) "
        f"status is now: {event.status.replace('_', ' ')}. "
        "Log in to your portal for details."
    )


# ── Content builders — Trade ───────────────────────────────────────────────

def _build_trade_content(event: TradeEvent) -> tuple[str, str, str]:
    """Return (subject, plain_text, html) for a trade confirmation email."""
    side_label = "Purchase" if event.side.upper() == "BUY" else "Sale"
    amount = event.quantity * event.price_inr

    subject = f"Aurum PMS — Trade Confirmation: {side_label} {event.security_symbol}"

    body_text = (
        f"Dear {event.client_name},\n\n"
        f"Your {side_label.lower()} order has been executed:\n\n"
        f"  Security:  {event.security_symbol}\n"
        f"  Side:      {event.side.upper()}\n"
        f"  Quantity:  {event.quantity:,.0f}\n"
        f"  Price:     ₹{event.price_inr:,.2f}\n"
        f"  Amount:    ₹{amount:,.2f}\n"
        f"  Account:   {event.account_code}\n"
        f"  Date:      {event.trade_date.strftime('%d %b %Y')}\n\n"
        "This is an automatically generated confirmation. "
        "Log in to your portal for full details.\n\n"
        "Best regards,\nAurum PMS"
    )

    body_html = _wrap_html_template(
        title=f"Trade Confirmation — {side_label}",
        greeting=f"Dear {event.client_name},",
        body=(
            f"<p>Your {side_label.lower()} order has been executed successfully.</p>"
            '<table style="width:100%;border-collapse:collapse;margin:16px 0;">'
            f'{_html_row("Security", event.security_symbol)}'
            f'{_html_row("Side", event.side.upper())}'
            f'{_html_row("Quantity", f"{event.quantity:,.0f}")}'
            f'{_html_row("Price", f"₹{event.price_inr:,.2f}")}'
            f'{_html_row("Amount", f"₹{amount:,.2f}")}'
            f'{_html_row("Account", event.account_code)}'
            f'{_html_row("Trade Date", event.trade_date.strftime("%d %b %Y"))}'
            "</table>"
        ),
        footer="This is an automatically generated confirmation. Log in to your portal for full details.",
    )

    return subject, body_text, body_html


def _build_trade_sms(event: TradeEvent) -> str:
    """Short SMS text for trade confirmation."""
    side = "Bought" if event.side.upper() == "BUY" else "Sold"
    amount = event.quantity * event.price_inr
    return (
        f"Aurum PMS: {side} {event.quantity:,.0f} {event.security_symbol} "
        f"@ ₹{event.price_inr:,.2f} (₹{amount:,.0f}) "
        f"in {event.account_code} on {event.trade_date.strftime('%d/%m/%Y')}."
    )


# ── HTML email template ────────────────────────────────────────────────────

def _html_row(label: str, value: str) -> str:
    return (
        "<tr>"
        f'<td style="padding:6px 12px;border-bottom:1px solid #eee;color:#666;width:120px;">{label}</td>'
        f'<td style="padding:6px 12px;border-bottom:1px solid #eee;font-weight:600;">{value}</td>'
        "</tr>"
    )


def _wrap_html_template(
    *,
    title: str,
    greeting: str,
    body: str,
    footer: str,
) -> str:
    """Wrap content in a branded Aurum PMS HTML email template."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);">
  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:24px 32px;text-align:center;">
      <span style="color:#d4af37;font-size:24px;font-weight:700;letter-spacing:1px;">AURUM</span>
      <span style="color:#9aa7bd;font-size:24px;font-weight:300;letter-spacing:1px;"> PMS</span>
    </td>
  </tr>
  <!-- Title bar -->
  <tr>
    <td style="background:#d4af37;padding:12px 32px;">
      <span style="color:#1a1a2e;font-size:16px;font-weight:600;">{title}</span>
    </td>
  </tr>
  <!-- Body -->
  <tr>
    <td style="padding:32px;">
      <p style="margin:0 0 16px;font-size:15px;color:#333;">{greeting}</p>
      {body}
    </td>
  </tr>
  <!-- Footer -->
  <tr>
    <td style="padding:20px 32px;background:#fafafa;border-top:1px solid #eee;">
      <p style="margin:0 0 8px;font-size:13px;color:#888;">{footer}</p>
      <p style="margin:0;font-size:12px;color:#aaa;">
        &copy; Aurum PMS &middot; SEBI Registered Portfolio Manager
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""
