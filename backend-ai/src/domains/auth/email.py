"""Email sender: stub-and-log in dev, SMTP/SES later.

Frontend builds the verify / reset URLs from the token; we just include
them in the body so curl-test flows can copy-paste.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


def _verify_url(token: str) -> str:
    base = get_settings().email_app_base_url.rstrip("/")
    return f"{base}/auth/verify-email?token={token}"


def _reset_url(token: str) -> str:
    base = get_settings().email_app_base_url.rstrip("/")
    return f"{base}/auth/reset-password?token={token}"


def _send(to: str, subject: str, body: str) -> bool:
    s = get_settings()
    if s.email_sender == "stub":
        logger.info("[email-stub] to=%s subject=%s\n%s", to, subject, body)
        return True
    if s.email_sender == "smtp":
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = s.email_from
            msg["To"] = to
            with smtplib.SMTP(s.smtp_host or "", s.smtp_port) as server:
                server.starttls()
                if s.smtp_username and s.smtp_password:
                    server.login(s.smtp_username, s.smtp_password)
                server.sendmail(s.email_from, [to], msg.as_string())
            return True
        except Exception as exc:
            logger.warning("smtp send failed (to=%s): %s", to, exc)
            return False
    if s.email_sender == "ses":
        try:
            import boto3  # type: ignore

            client = boto3.client("ses", region_name=s.ses_region or s.aws_region)
            client.send_email(
                Source=s.email_from,
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                },
            )
            return True
        except Exception as exc:
            logger.warning("ses send failed (to=%s): %s", to, exc)
            return False
    logger.warning("unknown email_sender=%s; dropping email to=%s", s.email_sender, to)
    return False


def send_verify_email(*, to: str, token: str, full_name: Optional[str] = None) -> bool:
    name = full_name or to
    url = _verify_url(token)
    body = (
        f"Hi {name},\n\n"
        "Welcome to EquityAI. Please verify your email by visiting:\n"
        f"  {url}\n\n"
        "This link expires in 24 hours. If you did not sign up, ignore this email.\n"
    )
    return _send(to=to, subject="Verify your EquityAI email", body=body)


def send_password_reset_email(*, to: str, token: str, full_name: Optional[str] = None) -> bool:
    name = full_name or to
    url = _reset_url(token)
    body = (
        f"Hi {name},\n\n"
        "Someone (hopefully you) requested a password reset. Reset by visiting:\n"
        f"  {url}\n\n"
        "This link expires in 30 minutes. If you did not request this, ignore.\n"
    )
    return _send(to=to, subject="Reset your EquityAI password", body=body)
