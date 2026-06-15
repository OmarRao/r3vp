"""
SOAR integration for R3VP.

Dispatches threat detection events to Splunk SOAR (Phantom) and
Palo Alto XSOAR (Cortex) via their REST APIs.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import structlog
import httpx

log = structlog.get_logger()


async def dispatch_to_splunk_soar(
    *,
    base_url: str,
    api_token: str,
    incident_title: str,
    severity: str,  # "critical", "high", "medium", "low"
    affected_host: str,
    threat_name: str,
    indicator_type: str,
    indicator_value: str,
    mitre_technique: str | None,
    org_id: str,
    finding_id: str,
) -> str | None:
    """
    Create an event/container in Splunk SOAR.

    Returns the SOAR container ID on success, or None on failure.
    """
    severity_map = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}
    payload = {
        "name": incident_title,
        "description": f"R3VP detected {threat_name} on {affected_host}. Indicator: {indicator_type}={indicator_value}",
        "severity": severity_map.get(severity, "medium"),
        "sensitivity": "amber",
        "tags": ["r3vp", "auto-generated"],
        "custom_fields": {
            "org_id": org_id,
            "r3vp_finding_id": finding_id,
            "affected_host": affected_host,
            "mitre_technique": mitre_technique or "",
        },
        "artifacts": [
            {
                "name": "Threat Indicator",
                "label": "artifact",
                "cef": {
                    "deviceHostname": affected_host,
                    "threatName": threat_name,
                    "indicatorType": indicator_type,
                    "indicatorValue": indicator_value,
                    "mitreId": mitre_technique or "",
                },
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/rest/container",
                json=payload,
                headers={
                    "ph-auth-token": api_token,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            container_id = str(data.get("id", ""))
            log.info("soar.splunk.dispatched", container_id=container_id)
            return container_id
    except Exception as exc:
        log.error("soar.splunk.failed", error=str(exc))
        return None


async def dispatch_to_xsoar(
    *,
    base_url: str,
    api_key: str,
    incident_title: str,
    severity: str,
    affected_host: str,
    threat_name: str,
    indicator_type: str,
    indicator_value: str,
    mitre_technique: str | None,
    org_id: str,
    finding_id: str,
) -> str | None:
    """
    Create an incident in Palo Alto XSOAR (Cortex).

    Returns the XSOAR incident ID on success, or None on failure.
    """
    severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    payload = {
        "name": incident_title,
        "type": "Malware",
        "severity": severity_map.get(severity, 2),
        "details": f"R3VP detected {threat_name} on {affected_host}. Indicator: {indicator_type}={indicator_value}",
        "labels": [
            {"type": "Instance", "value": affected_host},
            {"type": "r3vp_org", "value": org_id},
            {"type": "mitre_technique", "value": mitre_technique or ""},
        ],
        "CustomFields": {
            "r3vpfindingid": finding_id,
            "affectedhost": affected_host,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/incident",
                json=payload,
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            incident_id = str(data.get("id", ""))
            log.info("soar.xsoar.dispatched", incident_id=incident_id)
            return incident_id
    except Exception as exc:
        log.error("soar.xsoar.failed", error=str(exc))
        return None


async def dispatch_generic_webhook(
    *,
    webhook_url: str,
    incident_title: str,
    severity: str,
    affected_host: str,
    threat_name: str,
    indicator_type: str,
    indicator_value: str,
    mitre_technique: str | None,
    org_id: str,
    finding_id: str,
) -> bool:
    """Dispatch to a generic SOAR webhook (JSON POST)."""
    payload = {
        "source": "r3vp",
        "title": incident_title,
        "severity": severity,
        "affected_host": affected_host,
        "threat_name": threat_name,
        "indicator": {"type": indicator_type, "value": indicator_value},
        "mitre_technique": mitre_technique,
        "org_id": org_id,
        "finding_id": finding_id,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            log.info("soar.generic.dispatched", url=webhook_url)
            return True
    except Exception as exc:
        log.error("soar.generic.failed", error=str(exc))
        return False
