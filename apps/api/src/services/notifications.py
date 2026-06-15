"""Notification dispatch: email (SES), Slack webhook, Teams webhook."""
from __future__ import annotations

import structlog
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import NotificationChannel

log = structlog.get_logger()


async def send_breach_notifications(
    db: AsyncSession,
    org_id,
    workload_name: str,
    run_id: str,
    rto_target: int | None,
    rto_actual: int | None,
    rpo_target: int | None,
    rpo_actual: int | None,
    passed: bool,
) -> None:
    """Called after a test run finalises. Sends notifications for breaches."""
    events = set()
    if not passed:
        events.add("test_failed")
    if rto_target and rto_actual and rto_actual > rto_target:
        events.add("rto_breach")
    if rpo_target and rpo_actual and rpo_actual > rpo_target:
        events.add("rpo_breach")

    if not events:
        return

    channels = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.org_id == org_id,
            NotificationChannel.enabled.is_(True),
        )
    )

    for ch in channels.scalars().all():
        ch_events = set(ch.events or [])
        if not ch_events.intersection(events):
            continue
        try:
            await _dispatch(ch, workload_name, run_id, events, rto_target, rto_actual, rpo_target, rpo_actual)
        except Exception as exc:
            log.warning("notification dispatch failed", channel_id=str(ch.id), error=str(exc))


async def _dispatch(ch: NotificationChannel, workload_name: str, run_id: str,
                    events: set, rto_target, rto_actual, rpo_target, rpo_actual) -> None:
    summary_lines = []
    if "test_failed" in events:
        summary_lines.append("Recovery test FAILED")
    if "rto_breach" in events:
        summary_lines.append(f"RTO breach: actual {rto_actual} min, target {rto_target} min")
    if "rpo_breach" in events:
        summary_lines.append(f"RPO breach: actual {rpo_actual} min, target {rpo_target} min")
    summary = " | ".join(summary_lines)

    if ch.channel_type == "slack":
        await _send_slack(ch.destination, workload_name, run_id, summary)
    elif ch.channel_type == "teams":
        await _send_teams(ch.destination, workload_name, run_id, summary)
    elif ch.channel_type == "email":
        await _send_email_ses(ch.destination, workload_name, run_id, summary)
    else:
        log.warning("unknown notification channel type", channel_type=ch.channel_type)


async def _send_slack(webhook_url: str, workload_name: str, run_id: str, summary: str) -> None:
    payload = {
        "text": f":rotating_light: *R3VP Alert - {workload_name}*",
        "attachments": [
            {
                "color": "danger",
                "text": summary,
                "footer": f"Run ID: {run_id} | R3VP Recovery Validation",
            }
        ],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
    log.info("slack notification sent", workload=workload_name)


async def _send_teams(webhook_url: str, workload_name: str, run_id: str, summary: str) -> None:
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "FF0000",
        "summary": f"R3VP Alert - {workload_name}",
        "sections": [
            {
                "activityTitle": "R3VP Recovery Validation Alert",
                "activitySubtitle": workload_name,
                "facts": [
                    {"name": "Issue", "value": summary},
                    {"name": "Run ID", "value": run_id},
                ],
                "markdown": True,
            }
        ],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
    log.info("teams notification sent", workload=workload_name)


async def _send_email_ses(to_address: str, workload_name: str, run_id: str, summary: str) -> None:
    try:
        import boto3
        ses = boto3.client("ses", region_name="us-east-1")
        ses.send_email(
            Source="noreply@r3vp.io",
            Destination={"ToAddresses": [to_address]},
            Message={
                "Subject": {"Data": f"R3VP Alert: {workload_name}"},
                "Body": {
                    "Text": {
                        "Data": (
                            f"R3VP Recovery Validation Alert\n\n"
                            f"Workload: {workload_name}\n{summary}\n\nRun ID: {run_id}"
                        )
                    }
                },
            },
        )
        log.info("email notification sent via SES", to=to_address)
    except Exception as exc:
        log.warning("SES email failed", error=str(exc))
