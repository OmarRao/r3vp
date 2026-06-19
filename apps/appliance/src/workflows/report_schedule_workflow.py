"""Temporal workflow for scheduled compliance report delivery."""
from __future__ import annotations
import logging
from datetime import timedelta
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)

RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=30))


@activity.defn
async def fetch_schedule_config(schedule_id: str) -> dict:
    """Fetch schedule config and date range from the SaaS API."""
    import httpx
    import os
    from datetime import datetime, timezone, timedelta

    base = os.getenv("R3VP_API_URL", "https://api.r3vp.io")
    token = os.getenv("R3VP_APPLIANCE_TOKEN", "")
    async with httpx.AsyncClient(verify=True, timeout=30) as client:
        resp = await client.get(
            f"{base}/v1/report-schedules/{schedule_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        schedule = resp.json()

    now = datetime.now(timezone.utc)
    period_days = schedule.get("period_days", 30)
    to_date = now.strftime("%Y-%m-%d")
    from_date = (now - timedelta(days=period_days)).strftime("%Y-%m-%d")

    return {
        "schedule_id": schedule_id,
        "report_type": schedule["report_type"],
        "from_date": from_date,
        "to_date": to_date,
        "recipients": schedule["recipients"],
        "org_id": schedule["org_id"],
    }


@activity.defn
async def generate_and_deliver_report(config: dict) -> dict:
    """Generate the compliance PDF and deliver to all recipients."""
    import httpx
    import os
    from src.services.delivery import deliver_report, DeliveryRecipient

    base = os.getenv("R3VP_API_URL", "https://api.r3vp.io")
    token = os.getenv("R3VP_APPLIANCE_TOKEN", "")

    async with httpx.AsyncClient(verify=True, timeout=60) as client:
        resp = await client.post(
            f"{base}/v1/reports/compliance/generate",
            params={
                "report_type": config["report_type"],
                "from_date": config["from_date"],
                "to_date": config["to_date"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        pdf_bytes = resp.content
        report_id = resp.headers.get("X-Report-ID", "unknown")
        sha256 = resp.headers.get("X-SHA256", "unknown")

    filename = f"r3vp-{config['report_type']}-{config['from_date']}-{config['to_date']}.pdf"
    subject = f"R3VP Compliance Report: {config['report_type'].upper()} {config['from_date']} to {config['to_date']}"
    body = (
        f"Attached is your scheduled R3VP compliance report.\n\n"
        f"Period: {config['from_date']} to {config['to_date']}\n"
        f"Report ID: {report_id}\n"
        f"SHA-256: {sha256}\n\n"
        f"Verify this report has not been modified by checking the SHA-256 digest matches the attached PDF."
    )

    recipients = [DeliveryRecipient(type=r["type"], destination=r["destination"]) for r in config["recipients"]]
    results = await deliver_report(pdf_bytes, filename, subject, body, recipients)

    return {
        "report_id": report_id,
        "sha256": sha256,
        "delivered": [{"type": r.recipient.type, "destination": r.recipient.destination, "success": r.success} for r in results],
    }


@workflow.defn
class ReportScheduleWorkflow:
    @workflow.run
    async def run(self, schedule_id: str) -> dict:
        config = await workflow.execute_activity(
            fetch_schedule_config,
            schedule_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )
        result = await workflow.execute_activity(
            generate_and_deliver_report,
            config,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RETRY,
        )
        logger.info("Scheduled report delivered: %s", result)
        return result
