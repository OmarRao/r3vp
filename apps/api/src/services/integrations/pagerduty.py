"""PagerDuty Events API v2 integration."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations
import httpx
from typing import Any

SEVERITY_MAP = {"high": "critical", "medium": "warning", "low": "info"}


async def trigger_alert(config: dict, event_type: str, payload: dict[str, Any]) -> None:
    routing_key = config["routing_key"]
    severity = SEVERITY_MAP.get(payload.get("severity", "medium"), "warning")

    body = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": f"R3VP {event_type}: {payload.get('workload', payload.get('threat_name', 'unknown'))}",
            "source": "r3vp-appliance",
            "severity": severity,
            "custom_details": payload,
        },
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post("https://events.pagerduty.com/v2/enqueue", json=body)
        resp.raise_for_status()
