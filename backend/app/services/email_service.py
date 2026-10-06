from __future__ import annotations

import smtplib
from email.headerregistry import Address
from email.message import EmailMessage
from html import escape

from app.core.config import get_settings
from app.core.exceptions import AppError


class EmailService:
    @staticmethod
    def send_otp_email(email: str, otp: str, purpose: str = "verification") -> None:
        settings = get_settings()
        if not settings.smtp_host or not settings.smtp_from_email:
            raise AppError(
                "Email delivery is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL before requesting a verification code.",
                status_code=503,
            )

        safe_purpose = escape(purpose)
        message = EmailMessage()
        message["Subject"] = f"VehicleTracker | Your {purpose.title()} code"
        message["From"] = Address(settings.smtp_from_name, addr_spec=settings.smtp_from_email)
        message["To"] = email
        message.set_content(
            f"Your VehicleTracker {purpose} code is {otp}. It expires in {settings.otp_expiry_minutes} minutes."
        )
        message.add_alternative(
            f"""<!doctype html>
<html lang="en"><body style="margin:0;background:#f3f6fa;color:#1c2738;font-family:Arial,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:32px 12px;background:#f3f6fa"><tr><td align="center">
<table role="presentation" width="560" cellspacing="0" cellpadding="0" style="max-width:560px;width:100%;background:#fff;border:1px solid #dce4ee;border-radius:12px;overflow:hidden">
<tr><td style="padding:22px 28px;background:#123d78;color:#fff;font-size:20px;font-weight:bold">VehicleTracker</td></tr>
<tr><td style="padding:30px 28px 12px;font-size:22px;font-weight:bold">Verify your {safe_purpose}</td></tr>
<tr><td style="padding:0 28px 20px;color:#526176;font-size:15px;line-height:1.6">Use the verification code below to continue. For your security, do not share this code with anyone.</td></tr>
<tr><td align="center" style="padding:4px 28px 22px"><div style="display:inline-block;padding:14px 24px;background:#edf4ff;border:1px solid #d7e5fb;border-radius:8px;color:#154b9b;font-size:30px;font-weight:bold;letter-spacing:6px">{escape(otp)}</div></td></tr>
<tr><td style="padding:0 28px 26px;color:#526176;font-size:14px;line-height:1.6">This code expires in {settings.otp_expiry_minutes} minutes. If you did not request it, you can safely ignore this email.</td></tr>
<tr><td style="padding:16px 28px;border-top:1px solid #e8edf3;color:#78869a;font-size:12px">VehicleTracker account security</td></tr>
</table></td></tr></table></body></html>""",
            subtype="html",
        )

        try:
            if settings.smtp_port == 465:
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                    if settings.smtp_username:
                        smtp.login(settings.smtp_username, settings.smtp_password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    if settings.smtp_username:
                        smtp.login(settings.smtp_username, settings.smtp_password)
                    smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise AppError(
                "The verification email could not be delivered. Check the SMTP settings and try again.",
                status_code=503,
            ) from exc
