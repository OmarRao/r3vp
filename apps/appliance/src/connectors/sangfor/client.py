"""Sangfor HCI connector via REST API.

Communicates with Sangfor Hyper-Converged Infrastructure using its REST API.
Credentials and API spec must be provided by the Sangfor vendor or customer.
Supports VM inventory, snapshot operations, and basic health checks.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import structlog

from src.config import settings

log = structlog.get_logger()


@dataclass
class SangforVM:
    id: str
    name: str
    status: str
    cpu_num: int
    memory: int
    node_id: str
    ip_list: list[str] = field(default_factory=list)


@dataclass
class SangforSnapshot:
    id: str
    name: str
    vm_id: str
    create_time: str
    description: str
    size: int


@dataclass
class SangforTask:
    task_id: str
    status: str
    progress: int
    message: str


class SangforClient:
    """Client for Sangfor HCI via REST API."""

    def __init__(self) -> None:
        self._token: str = ""
        self._client: httpx.AsyncClient | None = None

    @property
    def _base_url(self) -> str:
        return f"https://{settings.sangfor_host}/api/v1"

    async def connect(self) -> bool:
        """Authenticate and store session token. Returns True on success."""
        try:
            self._client = httpx.AsyncClient(
                verify=settings.sangfor_verify_ssl,
                timeout=30.0,
            )
            resp = await self._client.post(
                f"{self._base_url}/auth/login",
                json={
                    "username": settings.sangfor_username,
                    "password": settings.sangfor_password.get_secret_value(),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("token", "")
            self._client.headers.update({"X-Auth-Token": self._token})
            return bool(self._token)
        except Exception as exc:
            log.error("sangfor connect failed", error=str(exc))
            if self._client:
                await self._client.aclose()
                self._client = None
            return False

    async def _get(self, path: str, **params) -> dict:
        """GET helper with token auth."""
        if self._client is None:
            raise AttributeError("not connected")
        resp = await self._client.get(f"{self._base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, body: dict) -> dict:
        """POST helper with token auth."""
        if self._client is None:
            raise AttributeError("not connected")
        resp = await self._client.post(f"{self._base_url}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    async def list_vms(self) -> list[SangforVM]:
        """Return all VMs from the Sangfor HCI platform."""
        try:
            data = await self._get("/vms")
            vms = data.get("data", [])
            return [
                SangforVM(
                    id=vm.get("id", ""),
                    name=vm.get("name", ""),
                    status=vm.get("status", ""),
                    cpu_num=int(vm.get("cpu_num", 0)),
                    memory=int(vm.get("memory", 0)),
                    node_id=vm.get("node_id", ""),
                    ip_list=vm.get("ip_list", []),
                )
                for vm in vms
            ]
        except AttributeError as exc:
            log.error("sangfor list_vms: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("sangfor list_vms failed", error=str(exc))
            return []

    async def get_vm_snapshots(self, vm_id: str) -> list[SangforSnapshot]:
        """Return all snapshots for a given VM ID."""
        try:
            data = await self._get(f"/vms/{vm_id}/snapshots")
            snaps = data.get("data", [])
            return [
                SangforSnapshot(
                    id=s.get("id", ""),
                    name=s.get("name", ""),
                    vm_id=vm_id,
                    create_time=s.get("create_time", ""),
                    description=s.get("description", ""),
                    size=int(s.get("size", 0)),
                )
                for s in snaps
            ]
        except AttributeError as exc:
            log.error("sangfor get_vm_snapshots: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("sangfor get_vm_snapshots failed", vm_id=vm_id, error=str(exc))
            return []

    async def create_snapshot(self, vm_id: str, name: str, description: str = "") -> str:
        """Create a snapshot for a VM. Returns the snapshot ID."""
        try:
            data = await self._post(
                f"/vms/{vm_id}/snapshots",
                {"name": name, "description": description},
            )
            return data.get("data", {}).get("id", "")
        except AttributeError as exc:
            log.error("sangfor create_snapshot: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error("sangfor create_snapshot failed", vm_id=vm_id, error=str(exc))
            return ""

    async def restore_vm_from_snapshot(
        self, vm_id: str, snapshot_id: str
    ) -> SangforTask:
        """Restore a VM from a snapshot. Returns a SangforTask."""
        try:
            data = await self._post(
                f"/vms/{vm_id}/snapshots/{snapshot_id}/restore", {}
            )
            task = data.get("data", {})
            return SangforTask(
                task_id=task.get("task_id", ""),
                status=task.get("status", ""),
                progress=int(task.get("progress", 0)),
                message=task.get("message", ""),
            )
        except AttributeError as exc:
            log.error("sangfor restore_vm_from_snapshot: not connected", error=str(exc))
            return SangforTask(task_id="", status="error", progress=0, message=str(exc))
        except Exception as exc:
            log.error(
                "sangfor restore_vm_from_snapshot failed",
                vm_id=vm_id,
                snapshot_id=snapshot_id,
                error=str(exc),
            )
            return SangforTask(task_id="", status="error", progress=0, message=str(exc))

    async def get_task_status(self, task_id: str) -> SangforTask:
        """Return the status of a Sangfor task."""
        try:
            data = await self._get(f"/tasks/{task_id}")
            task = data.get("data", {})
            return SangforTask(
                task_id=task_id,
                status=task.get("status", ""),
                progress=int(task.get("progress", 0)),
                message=task.get("message", ""),
            )
        except AttributeError as exc:
            log.error("sangfor get_task_status: not connected", error=str(exc))
            return SangforTask(task_id=task_id, status="error", progress=0, message=str(exc))
        except Exception as exc:
            log.error("sangfor get_task_status failed", task_id=task_id, error=str(exc))
            return SangforTask(task_id=task_id, status="error", progress=0, message=str(exc))

    async def get_vm_health(self, vm_id: str) -> dict:
        """Return basic health info for a VM."""
        try:
            data = await self._get(f"/vms/{vm_id}")
            vm = data.get("data", {})
            return {
                "status": vm.get("status", ""),
                "name": vm.get("name", ""),
                "ip_list": vm.get("ip_list", []),
            }
        except AttributeError as exc:
            log.error("sangfor get_vm_health: not connected", error=str(exc))
            return {}
        except Exception as exc:
            log.error("sangfor get_vm_health failed", vm_id=vm_id, error=str(exc))
            return {}
