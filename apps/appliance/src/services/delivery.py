"""Report delivery: send a generated report to configured recipients.

Supports email (SMTP), Slack, Microsoft Teams, and generic webhook channels.
Each recipient is delivered independently; a failure for one recipient does not
abort the others, and the per-recipient outcome is returned so callers can
record an accurate delivery status.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DeliveryRecipient:
    """A single delivery target: a channel type and its destination."""

    type: str          # "email" | "slack" | "teams" | "webhook"
    destination: str   # email address or webhook URL


@dataclass
class DeliveryResult:
    """Outcome of delivering to one recipient."""

    recipient: DeliveryRecipient
    success: bool
    error: str | None = None


async def deliver_report(
    pdf_bytes: bytes,
    filename: str,
    subject: str,
    body: str,
    recipients: list[DeliveryRecipient],
) -> list[DeliveryResult]:
    """Deliver a report to every recipient, returning a per-recipient result."""
    results: list[DeliveryResult] = []
    for recipient in recipients:
        try:
            if recipient.type == "email":
                _send_email(recipient.destination, subject, body, pdf_bytes, filename)
            elif recipient.type in ("slack", "teams", "webhook"):
                await _post_webhook(recipient.type, recipient.destination, subject, body)
            else:
                raise ValueError(f"Unknown recipient type: {recipient.type}")
            results.append(DeliveryResult(recipient=recipient, success=True))
        except Exception as exc:  # noqa: BLE001 - record per-recipient failure
            logger.warning("report delivery failed: %s -> %s", recipient.type, exc)
            results.append(DeliveryResult(recipient=recipient, success=False, error=str(exc)))
    return results


def _send_email(to_address: str, subject: str, body: str, pdf_bytes: bytes, filename: str) -> None:
    """Send the report as an email with the PDF attached, via SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("SMTP_FROM", "r3vp@example.com")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain"))
    if pdf_bytes:
        attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename=filename or "report.pdf")
        msg.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        if smtp_user:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)
    logger.info("report emailed to %s", to_address)


async def _post_webhook(channel: str, url: str, subject: str, body: str) -> None:
    """Post a report-ready notification to a Slack/Teams/generic webhook."""
    if channel == "teams":
        payload: dict = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": subject,
            "sections": [{"activityTitle": subject, "text": body, "markdown": True}],
        }
    elif channel == "slack":
        payload = {"text": f"*{subject}*\n{body}"}
    else:  # generic webhook
        payload = {"source": "r3vp", "event": "report_delivered", "subject": subject, "body": body}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
    logger.info("report notification posted to %s webhook", channel)
