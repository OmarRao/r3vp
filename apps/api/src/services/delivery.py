"""Report delivery service: email, Slack, and Teams."""
from __future__ import annotations
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeliveryRecipient:
    type: str  # email | slack | teams
    destination: str  # email address, Slack webhook URL, or Teams webhook URL


@dataclass
class DeliveryResult:
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
    """Deliver a PDF report to a list of recipients via their configured channel."""
    results: list[DeliveryResult] = []
    for recipient in recipients:
        try:
            if recipient.type == "email":
                result = await _send_email(pdf_bytes, filename, subject, body, recipient.destination)
            elif recipient.type == "slack":
                result = await _send_slack(pdf_bytes, filename, subject, body, recipient.destination)
            elif recipient.type == "teams":
                result = await _send_teams(pdf_bytes, filename, subject, body, recipient.destination)
            else:
                result = DeliveryResult(recipient=recipient, success=False, error=f"Unknown channel type: {recipient.type}")
            results.append(result)
        except Exception as exc:
            logger.exception("Delivery failed for %s %s", recipient.type, recipient.destination)
            results.append(DeliveryResult(recipient=recipient, success=False, error=str(exc)))
    return results


async def _send_email(pdf_bytes: bytes, filename: str, subject: str, body: str, address: str) -> DeliveryResult:
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("SMTP_FROM", "r3vp@example.com")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = address
    msg.attach(MIMEText(body, "plain"))
    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        if smtp_user:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)

    return DeliveryResult(recipient=DeliveryRecipient(type="email", destination=address), success=True)


async def _send_slack(pdf_bytes: bytes, filename: str, subject: str, body: str, webhook_url: str) -> DeliveryResult:
    import httpx
    recipient = DeliveryRecipient(type="slack", destination=webhook_url)
    payload = {
        "text": f":page_facing_up: *{subject}*\n{body}\n_PDF report attached as `{filename}`_"
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
    return DeliveryResult(recipient=recipient, success=True)


async def _send_teams(pdf_bytes: bytes, filename: str, subject: str, body: str, webhook_url: str) -> DeliveryResult:
    import httpx
    recipient = DeliveryRecipient(type="teams", destination=webhook_url)
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": subject,
        "themeColor": "00B336",
        "sections": [{"activityTitle": subject, "activityText": body, "facts": [{"name": "Report", "value": filename}]}],
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
    return DeliveryResult(recipient=recipient, success=True)
