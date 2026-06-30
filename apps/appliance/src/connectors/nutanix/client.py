"""Nutanix AHV connector via Prism Central REST API v3.

Communicates with Nutanix Prism Central using basic auth over HTTPS.
Supports VM inventory, snapshot (recovery point) management, and restore.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from src.config import settings

log = structlog.get_logger()


@dataclass
class NutanixVM:
    uuid: str
    name: str
    power_state: str
    num_vcpus: int
    memory_size_mib: int
    cluster_uuid: str
    hypervisor_type: str = "AHV"


@dataclass
class NutanixRecoveryPoint:
    uuid: str
    name: str
    creation_time: str
    vm_uuid: str
    recovery_point_type: str


@dataclass
class NutanixRestoreJob:
    task_uuid: str
    status: str
    vm_uuid: str
    started_at: str


class NutanixClient:
    """Client for Nutanix Prism Central via the v3 REST API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def _base_url(self) -> str:
        return f"https://{settings.nutanix_prism_host}:9440/api/nutanix/v3"

    async def connect(self) -> bool:
        """Verify connectivity to Prism Central. Returns True on success."""
        try:
            auth = (
                settings.nutanix_username,
                settings.nutanix_password.get_secret_value(),
            )
            self._client = httpx.AsyncClient(
                auth=auth,
                verify=settings.nutanix_verify_ssl,
                timeout=30.0,
            )
            resp = await self._client.post(f"{self._base_url}/users/me", json={})
            resp.raise_for_status()
            return True
        except Exception as exc:
            log.error("nutanix connect failed", error=str(exc))
            if self._client:
                await self._client.aclose()
                self._client = None
            return False

    async def list_vms(self, limit: int = 500) -> list[NutanixVM]:
        """Return all VMs from Prism Central."""
        try:
            if self._client is None:
                raise AttributeError("not connected")
            resp = await self._client.post(
                f"{self._base_url}/vms/list",
                json={"kind": "vm", "length": limit},
            )
            resp.raise_for_status()
            entities = resp.json().get("entities", [])
            result = []
            for e in entities:
                spec = e.get("spec", {})
                resources = spec.get("resources", {})
                cluster_ref = spec.get("cluster_reference", {})
                result.append(
                    NutanixVM(
                        uuid=e.get("metadata", {}).get("uuid", ""),
                        name=spec.get("name", ""),
                        power_state=resources.get("power_state", ""),
                        num_vcpus=int(resources.get("num_vcpus_per_socket", 1))
                        * int(resources.get("num_sockets", 1)),
                        memory_size_mib=int(resources.get("memory_size_mib", 0)),
                        cluster_uuid=cluster_ref.get("uuid", ""),
                    )
                )
            return result
        except AttributeError as exc:
            log.error("nutanix list_vms: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("nutanix list_vms failed", error=str(exc))
            return []

    async def list_recovery_points(self, vm_uuid: str) -> list[NutanixRecoveryPoint]:
        """Return recovery points for a given VM UUID."""
        try:
            if self._client is None:
                raise AttributeError("not connected")
            resp = await self._client.post(
                f"{self._base_url}/recovery_points/list",
                json={"kind": "recovery_point", "filter": f"vm_uuid=={vm_uuid}"},
            )
            resp.raise_for_status()
            entities = resp.json().get("entities", [])
            result = []
            for e in entities:
                meta = e.get("metadata", {})
                spec = e.get("spec", {})
                resources = spec.get("resources", {})
                result.append(
                    NutanixRecoveryPoint(
                        uuid=meta.get("uuid", ""),
                        name=spec.get("name", ""),
                        creation_time=meta.get("creation_time", ""),
                        vm_uuid=vm_uuid,
                        recovery_point_type=resources.get("recovery_point_type", ""),
                    )
                )
            return result
        except AttributeError as exc:
            log.error("nutanix list_recovery_points: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("nutanix list_recovery_points failed", vm_uuid=vm_uuid, error=str(exc))
            return []

    async def create_recovery_point(self, vm_uuid: str, name: str) -> str:
        """Create a recovery point for the given VM. Returns the new recovery point UUID."""
        try:
            if self._client is None:
                raise AttributeError("not connected")
            body = {
                "spec": {
                    "name": name,
                    "resources": {
                        "recovery_point_type": "CRASH_CONSISTENT",
                        "vm_recovery_point_list": [{"vm_uuid": vm_uuid}],
                    },
                },
                "metadata": {"kind": "recovery_point"},
            }
            resp = await self._client.post(f"{self._base_url}/recovery_points", json=body)
            resp.raise_for_status()
            return resp.json().get("metadata", {}).get("uuid", "")
        except AttributeError as exc:
            log.error("nutanix create_recovery_point: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error("nutanix create_recovery_point failed", vm_uuid=vm_uuid, error=str(exc))
            return ""

    async def restore_vm(
        self, recovery_point_uuid: str, target_cluster_uuid: str
    ) -> NutanixRestoreJob:
        """Restore a VM from a recovery point. Returns a NutanixRestoreJob."""
        try:
            if self._client is None:
                raise AttributeError("not connected")
            body = {
                "cluster_reference": {
                    "kind": "cluster",
                    "uuid": target_cluster_uuid,
                }
            }
            resp = await self._client.post(
                f"{self._base_url}/recovery_points/{recovery_point_uuid}/restore",
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return NutanixRestoreJob(
                task_uuid=data.get("task_uuid", ""),
                status="RUNNING",
                vm_uuid="",
                started_at=data.get("start_time", ""),
            )
        except AttributeError as exc:
            log.error("nutanix restore_vm: not connected", error=str(exc))
            return NutanixRestoreJob(task_uuid="", status="ERROR", vm_uuid="", started_at="")
        except Exception as exc:
            log.error(
                "nutanix restore_vm failed",
                recovery_point_uuid=recovery_point_uuid,
                error=str(exc),
            )
            return NutanixRestoreJob(task_uuid="", status="ERROR", vm_uuid="", started_at="")

    async def get_task_status(self, task_uuid: str) -> str:
        """Return the status string for a Prism task."""
        try:
            if self._client is None:
                raise AttributeError("not connected")
            resp = await self._client.get(f"{self._base_url}/tasks/{task_uuid}")
            resp.raise_for_status()
            return resp.json().get("status", "")
        except AttributeError as exc:
            log.error("nutanix get_task_status: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error("nutanix get_task_status failed", task_uuid=task_uuid, error=str(exc))
            return ""

    async def get_vm_health(self, vm_uuid: str) -> dict:
        """Return basic health info for a VM."""
        try:
            if self._client is None:
                raise AttributeError("not connected")
            resp = await self._client.get(f"{self._base_url}/vms/{vm_uuid}")
            resp.raise_for_status()
            data = resp.json()
            spec = data.get("spec", {})
            resources = spec.get("resources", {})
            return {
                "power_state": resources.get("power_state", ""),
                "name": spec.get("name", ""),
            }
        except AttributeError as exc:
            log.error("nutanix get_vm_health: not connected", error=str(exc))
            return {}
        except Exception as exc:
            log.error("nutanix get_vm_health failed", vm_uuid=vm_uuid, error=str(exc))
            return {}
