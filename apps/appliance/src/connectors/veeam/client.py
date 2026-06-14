"""Veeam Backup & Replication REST API v1.1 connector.

Handles auth token lifecycle, retries, and maps Veeam API responses
into the platform's internal data models.
"""
from __future__ import annotations

import httpx
import structlog
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from .models import VeeamJob, VeeamVM, VeeamRestorePoint

log = structlog.get_logger()

_TOKEN_ENDPOINT = "/api/oauth2/token"
_API_BASE = "/api/v1"


class VeeamClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.veeam_base_url,
            verify=False,  # Veeam often uses self-signed certs on-prem
            timeout=60.0,
        )
        self._token: str | None = None
        self._token_expires: datetime = datetime.min

    async def __aenter__(self) -> VeeamClient:
        await self._ensure_token()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    async def _ensure_token(self) -> None:
        if self._token and datetime.utcnow() < self._token_expires - timedelta(minutes=2):
            return
        resp = await self._http.post(
            _TOKEN_ENDPOINT,
            data={
                "grant_type": "password",
                "username": settings.veeam_username,
                "password": settings.veeam_password.get_secret_value(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires = datetime.utcnow() + timedelta(seconds=body.get("expires_in", 900))
        self._http.headers["Authorization"] = f"Bearer {self._token}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(self, path: str, **params: object) -> dict:
        await self._ensure_token()
        resp = await self._http.get(f"{_API_BASE}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _post(self, path: str, body: dict) -> dict:
        await self._ensure_token()
        resp = await self._http.post(f"{_API_BASE}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    async def list_jobs(self) -> list[VeeamJob]:
        data = await self._get("/jobs")
        return [VeeamJob.model_validate(j) for j in data.get("data", [])]

    async def list_protected_vms(self) -> list[VeeamVM]:
        data = await self._get("/protectedVMs")
        return [VeeamVM.model_validate(v) for v in data.get("data", [])]

    async def list_restore_points(self, object_id: str) -> list[VeeamRestorePoint]:
        data = await self._get("/restorePoints", objectId=object_id)
        return [VeeamRestorePoint.model_validate(r) for r in data.get("data", [])]

    async def start_instant_recovery(
        self,
        restore_point_id: str,
        target_datastore: str,
        isolated_network: str,
    ) -> str:
        """Start instant VM recovery into the isolated network. Returns session ID."""
        body = {
            "restorePointId": restore_point_id,
            "targetDatastoreId": target_datastore,
            "networkMapping": [{"sourceNetwork": "*", "targetNetwork": isolated_network}],
            "powerOn": True,
            "reason": "R3VP automated recovery validation",
        }
        data = await self._post("/instantRecovery/vmware/vm", body)
        return data["sessionId"]

    async def get_session_state(self, session_id: str) -> str:
        data = await self._get(f"/sessions/{session_id}")
        return data.get("state", "unknown")

    async def stop_instant_recovery(self, session_id: str) -> None:
        await self._post(f"/instantRecovery/vmware/vm/{session_id}/stopPublishing", {})
