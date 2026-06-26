"""Quick test: send an email via Gmail SMTP to verify the App Password works."""
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "aarya.moodi@gmail.com"
SMTP_PASSWORD = "uedv zowu tkjo vuhf"

TO_EMAIL = "aariiparekh3012@gmail.com"  # your inbox

msg = EmailMessage()
msg["From"] = f"Aurum PMS <{SMTP_USER}>"
msg["To"] = TO_EMAIL
msg["Subject"] = "Aurum PMS - Email Test"
msg.set_content("If you see this, Gmail SMTP is working correctly!")

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    print("SUCCESS - email sent! Check your inbox.")
except Exception as e:
    print(f"FAILED: {e}")
