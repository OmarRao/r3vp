"""Veeam Backup & Replication REST API connector with version detection.

Handles auth token lifecycle, retries, version-aware API path selection,
and maps Veeam API responses into the platform's internal data models.

Supports Veeam 11 (v1.0), Veeam 12 (v1.1), and Veeam 13.0.2+ (v1.2).

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import httpx
import structlog
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from .models import VeeamJob, VeeamVM, VeeamRestorePoint, VeeamRepository, VeeamMalwareEvent, VeeamJobSession

log = structlog.get_logger()

_TOKEN_ENDPOINT = "/api/oauth2/token"
_API_BASE = "/api/v1"
_SERVER_INFO_PATH = "/api/v1/serverInfo"


class VeeamClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.veeam_base_url,
            verify=False,  # Veeam often uses self-signed certs on-prem
            timeout=60.0,
        )
        self._token: str | None = None
        self._token_expires: datetime = datetime.min
        self._build_version: str | None = None
        self._vbr_id: str | None = None
        self._server_name: str | None = None

    @property
    def api_version(self) -> str:
        """Return the effective API version string based on the detected build version.

        Returns 'v1.2' for Veeam 13.x, 'v1.1' for Veeam 12.x, 'v1.0' for anything older.
        If version has not been detected yet, defaults to 'v1.1'.
        """
        if self._build_version:
            major = self._build_version.split(".")[0]
            if major == "13":
                return "v1.2"
            if major == "12":
                return "v1.1"
        return "v1.0"

    async def __aenter__(self) -> VeeamClient:
        await self._ensure_token()
        await self._fetch_server_info()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    async def _fetch_server_info(self) -> None:
        """Fetch server build version and VBR ID from the serverInfo endpoint."""
        try:
            resp = await self._http.get(_SERVER_INFO_PATH)
            resp.raise_for_status()
            body = resp.json()
            self._build_version = body.get("buildVersion")
            self._vbr_id = body.get("vbrId")
            self._server_name = body.get("name")
            log.info(
                "veeam_server_info_detected",
                build_version=self._build_version,
                vbr_id=self._vbr_id,
                api_version=self.api_version,
            )
        except Exception as exc:
            log.warning("veeam_server_info_unavailable", error=str(exc))

    async def detect_version(self) -> dict:
        """Return a dict with build_version, api_version, and server_name.

        Triggers a fresh serverInfo fetch if version has not been loaded yet.
        """
        if not self._build_version:
            await self._fetch_server_info()
        return {
            "build_version": self._build_version,
            "api_version": self.api_version,
            "server_name": self._server_name,
        }

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
        """Fetch restore points for a backup object, using the version-appropriate API path.

        Veeam 12 (v1.1) and Veeam 13 (v1.2): GET /backupObjects/{objectId}/restorePoints
        Veeam 11 (v1.0): GET /restorePoints?backupObjectId={objectId}
        v1.2 uses the same path as v1.1 -- no change needed for Veeam 13.
        """
        if self.api_version in ("v1.1", "v1.2"):
            data = await self._get(f"/backupObjects/{object_id}/restorePoints")
        else:
            data = await self._get("/restorePoints", backupObjectId=object_id)
        return [VeeamRestorePoint.model_validate(r) for r in data.get("data", [])]

    async def start_instant_recovery(
        self,
        restore_point_id: str,
        target_datastore: str,
        isolated_network: str,
    ) -> str:
        """Start instant VM recovery into the isolated network. Returns session ID.

        Raises NotImplementedError if the connected Veeam server does not support
        the instant recovery API (requires Veeam 11 or later).
        """
        if self.api_version == "v1.0":
            raise NotImplementedError("Instant recovery API requires Veeam 11+")
        body = {
            "restorePointId": restore_point_id,
            "targetDatastoreId": target_datastore,
            "networkMapping": [{"sourceNetwork": "*", "targetNetwork": isolated_network}],
            "powerOn": True,
            "reason": "R3VP automated recovery validation",
        }
        # Veeam 13 (v1.2) renamed the endpoint; v1.1 and earlier use the vmware-specific path
        if self.api_version == "v1.2":
            endpoint = "/instantRecovery/vm"
        else:
            endpoint = "/instantRecovery/vmware/vm"
        data = await self._post(endpoint, body)
        return data["sessionId"]

    async def get_session_state(self, session_id: str) -> str:
        data = await self._get(f"/sessions/{session_id}")
        return data.get("state", "unknown")

    async def stop_instant_recovery(self, session_id: str) -> None:
        if self.api_version == "v1.2":
            await self._post(f"/instantRecovery/vm/{session_id}/stopPublishing", {})
        else:
            await self._post(f"/instantRecovery/vmware/vm/{session_id}/stopPublishing", {})

    async def list_backup_repositories(self) -> list[dict]:
        """List all backup repositories. Requires Veeam 13 (v1.2)."""
        if self.api_version != "v1.2":
            return []
        data = await self._get("/backupRepositories")
        return data.get("data", [])

    async def list_malware_detection_events(self, limit: int = 50) -> list[dict]:
        """
        Fetch inline malware detection events from Veeam 13's built-in scanner.
        Requires Veeam 13 (v1.2). Returns empty list on older versions.
        """
        if self.api_version != "v1.2":
            return []
        data = await self._get("/malwareDetection/events", limit=limit)
        return data.get("data", [])

    async def trigger_backup_job(self, job_id: str) -> str:
        """Start a backup job immediately. Returns the session ID."""
        data = await self._post(f"/jobs/{job_id}/start", {})
        return data.get("sessionId", "")

    async def get_backup_job_session(self, session_id: str) -> dict:
        """Get current state of a backup job session."""
        return await self._get(f"/jobSessions/{session_id}")

    async def list_backup_objects(self) -> list[dict]:
        """List all backup objects (protected VMs/workloads) with full metadata."""
        data = await self._get("/backupObjects")
        return data.get("data", [])
