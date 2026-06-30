"""Splunk HEC and CEF Syslog integrations."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations

import time
from typing import Any

import httpx


async def send_hec_event(config: dict, event_type: str, payload: dict[str, Any]) -> None:
    hec_url = config["hec_url"].rstrip("/")
    token = config["hec_token"]
    index = config.get("index", "main")

    body = {
        "time": time.time(),
        "source": "r3vp",
        "sourcetype": "r3vp:event",
        "index": index,
        "event": {"event_type": event_type, **payload},
    }
    async with httpx.AsyncClient(timeout=15, verify=config.get("verify_ssl", True)) as client:
        resp = await client.post(
            f"{hec_url}/services/collector/event",
            headers={"Authorization": f"Splunk {token}"},
            json=body,
        )
        resp.raise_for_status()


async def send_syslog_cef(config: dict, event_type: str, payload: dict[str, Any]) -> None:
    """CEF over syslog UDP/TCP for QRadar."""
    import socket
    host = config["syslog_host"]
    port = int(config.get("syslog_port", 514))
    severity = 5 if payload.get("severity") == "high" else 3

    cef = (
        f"CEF:0|R3VP|RecoveryValidation|1.0|{event_type}|{event_type}|{severity}|"
        + " ".join(f"{k}={str(v).replace(' ', '_')}" for k, v in payload.items())
    )
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(cef.encode(), (host, port))
