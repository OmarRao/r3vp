"""ServiceNow CMDB and Incident integration."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations

from typing import Any

import httpx

SEVERITY_MAP = {"high": "1", "medium": "2", "low": "3"}


async def send_incident(config: dict, event_type: str, payload: dict[str, Any]) -> None:
    instance = config["instance_url"].rstrip("/")
    token = config["api_token"]
    table = "incident"

    title = _build_title(event_type, payload)
    description = _build_description(event_type, payload)
    severity = SEVERITY_MAP.get(payload.get("severity", "medium"), "2")

    body = {
        "short_description": title,
        "description": description,
        "urgency": severity,
        "impact": severity,
        "category": "Software",
        "subcategory": "Backup and Recovery",
        "caller_id": config.get("caller_id", "r3vp"),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{instance}/api/now/table/{table}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()


def _build_title(event_type: str, payload: dict) -> str:
    if event_type == "sla_breach":
        return f"R3VP: RTO SLA breach - {payload.get('workload', 'unknown')}"
    if event_type == "test_failed":
        return f"R3VP: Recovery test failed - {payload.get('workload', 'unknown')}"
    if event_type == "threat_detected":
        return f"R3VP: Threat detected - {payload.get('threat_name', 'unknown')}"
    return f"R3VP: {event_type} - {payload.get('workload', '')}"


def _build_description(event_type: str, payload: dict) -> str:
    lines = [f"Event: {event_type}"]
    for k, v in payload.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)
