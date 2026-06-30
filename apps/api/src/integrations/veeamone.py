"""
VeeamONE integration for R3VP.

Pushes recovery test results and threat detection events to VeeamONE
via its REST API, making R3VP data visible in VeeamONE dashboards.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger()


class VeeamOneClient:
    """Client for the VeeamONE REST API."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._token: str | None = None

    async def _authenticate(self) -> str:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/api/token",
                data={
                    "grant_type": "password",
                    "username": self._username,
                    "password": self._password,
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    async def _headers(self) -> dict:
        if not self._token:
            await self._authenticate()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def report_recovery_test(
        self,
        *,
        workload_name: str,
        test_passed: bool,
        rto_actual_mins: int,
        rpo_actual_mins: int,
        rto_target_mins: int | None,
        rpo_target_mins: int | None,
        run_id: str,
        org_id: str,
    ) -> bool:
        """Post a recovery test result to VeeamONE as a custom alarm/event."""
        alarm_status = "Resolved" if test_passed else "Error"
        payload = {
            "alarmName": "R3VP Recovery Test",
            "objectName": workload_name,
            "status": alarm_status,
            "message": (
                f"R3VP recovery test {'passed' if test_passed else 'failed'} for {workload_name}. "
                f"RTO: {rto_actual_mins}m (target: {rto_target_mins or 'N/A'}m), "
                f"RPO: {rpo_actual_mins}m (target: {rpo_target_mins or 'N/A'}m). "
                f"Run ID: {run_id}"
            ),
            "customFields": {
                "r3vp_run_id": run_id,
                "r3vp_org_id": org_id,
                "rto_actual_mins": rto_actual_mins,
                "rpo_actual_mins": rpo_actual_mins,
            },
        }
        return await self._post_event(payload)

    async def report_threat_event(
        self,
        *,
        threat_name: str,
        severity: str,
        affected_host: str,
        mitre_technique: str | None,
        finding_id: str,
        org_id: str,
    ) -> bool:
        """Post a threat detection event to VeeamONE."""
        payload = {
            "alarmName": "R3VP Threat Detection",
            "objectName": affected_host,
            "status": "Error" if severity in ("critical", "high") else "Warning",
            "message": (
                f"R3VP detected threat on {affected_host}: {threat_name}. "
                f"Severity: {severity}. "
                f"MITRE: {mitre_technique or 'N/A'}. "
                f"Finding ID: {finding_id}"
            ),
            "customFields": {
                "r3vp_finding_id": finding_id,
                "r3vp_org_id": org_id,
                "threat_name": threat_name,
                "severity": severity,
            },
        }
        return await self._post_event(payload)

    async def _post_event(self, payload: dict) -> bool:
        try:
            headers = await self._headers()
            async with httpx.AsyncClient(verify=False, timeout=15) as client:
                resp = await client.post(
                    f"{self._base_url}/api/v2/alarms/customAlarms",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                log.info("veeamone.event.sent", alarm=payload.get("alarmName"))
                return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                # Token expired, re-authenticate and retry once
                self._token = None
                try:
                    headers = await self._headers()
                    async with httpx.AsyncClient(verify=False, timeout=15) as client:
                        resp = await client.post(
                            f"{self._base_url}/api/v2/alarms/customAlarms",
                            json=payload,
                            headers=headers,
                        )
                        resp.raise_for_status()
                        return True
                except Exception as retry_exc:
                    log.error("veeamone.event.failed", error=str(retry_exc))
                    return False
            log.error("veeamone.event.failed", error=str(exc))
            return False
        except Exception as exc:
            log.error("veeamone.event.failed", error=str(exc))
            return False
