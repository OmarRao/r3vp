"""Jira issue creation integration."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations
import httpx
from typing import Any


async def create_issue(config: dict, event_type: str, payload: dict[str, Any]) -> None:
    base = config["base_url"].rstrip("/")
    token = config["api_token"]
    email = config["email"]
    project_key = config["project_key"]

    title = _build_summary(event_type, payload)
    description = _build_description(event_type, payload)
    priority = "High" if payload.get("severity") == "high" else "Medium"

    body = {
        "fields": {
            "project": {"key": project_key},
            "summary": title,
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]},
            "issuetype": {"name": "Bug"},
            "priority": {"name": priority},
            "labels": ["r3vp", event_type.replace("_", "-")],
        }
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base}/rest/api/3/issue",
            headers={"Content-Type": "application/json"},
            auth=(email, token),
            json=body,
        )
        resp.raise_for_status()


def _build_summary(event_type: str, payload: dict) -> str:
    if event_type == "sla_breach":
        return f"[R3VP] RTO SLA breach: {payload.get('workload', 'unknown')}"
    if event_type == "test_failed":
        return f"[R3VP] Recovery test failed: {payload.get('workload', 'unknown')}"
    return f"[R3VP] {event_type}: {payload.get('workload', '')}"


def _build_description(event_type: str, payload: dict) -> str:
    return "\n".join(f"*{k}:* {v}" for k, v in payload.items())
