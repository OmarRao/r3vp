"""Microsoft Sentinel Log Analytics integration."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations
import hashlib
import hmac
import base64
import json
import time
import httpx
from datetime import datetime, timezone
from typing import Any


async def send_log_analytics(config: dict, event_type: str, payload: dict[str, Any]) -> None:
    workspace_id = config["workspace_id"]
    shared_key = config["shared_key"]
    log_type = config.get("log_type", "R3VP")

    body = json.dumps([{"EventType": event_type, **payload}])
    rfc1123 = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    content_length = len(body.encode("utf-8"))
    string_to_sign = f"POST\n{content_length}\napplication/json\nx-ms-date:{rfc1123}\n/api/logs"
    signature = base64.b64encode(
        hmac.new(base64.b64decode(shared_key), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://{workspace_id}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01",
            headers={
                "Content-Type": "application/json",
                "Log-Type": log_type,
                "x-ms-date": rfc1123,
                "Authorization": f"SharedKey {workspace_id}:{signature}",
            },
            data=body.encode("utf-8"),
        )
        resp.raise_for_status()
