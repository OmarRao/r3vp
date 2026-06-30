"""Citrix Hypervisor / XenServer connector via XenAPI (XML-RPC).

Communicates with XenServer using the XML-RPC based XenAPI.
Supports VM inventory, snapshot management, and restore operations.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

from src.config import settings

log = structlog.get_logger()


@dataclass
class XenVM:
    uuid: str
    name_label: str
    power_state: str
    memory_static_max: int
    vcpus_max: int
    resident_on: str


@dataclass
class XenSnapshot:
    uuid: str
    name_label: str
    name_description: str
    snapshot_time: str
    snapshot_of: str


@dataclass
class XenTask:
    uuid: str
    status: str
    progress: float
    result: str


class XenServerClient:
    """Client for Citrix Hypervisor / XenServer via the XenAPI XML-RPC interface."""

    def __init__(self) -> None:
        self._session = None

    @property
    def _xe(self):
        """Shorthand for self._session.xenapi."""
        return self._session.xenapi

    def connect(self) -> bool:
        """Connect to XenServer. Returns True on success."""
        try:
            import XenAPI  # type: ignore
        except ImportError:
            log.warning(
                "XenAPI module not installed - download from XenServer SDK"
            )
            return False
        try:
            session = XenAPI.Session(f"http://{settings.xenserver_host}")
            session.xenapi.login_with_password(
                settings.xenserver_username,
                settings.xenserver_password.get_secret_value(),
                "1.0",
                "R3VP",
            )
            self._session = session
            return True
        except Exception as exc:
            log.error("xenserver connect failed", error=str(exc))
            return False

    def list_vms(self) -> list[XenVM]:
        """Return all non-template, non-control-domain VMs."""
        try:
            if self._session is None:
                raise AttributeError("not connected")
            all_records = self._xe.VM.get_all_records()
            result = []
            for _ref, rec in all_records.items():
                if rec.get("is_a_template") or rec.get("is_control_domain"):
                    continue
                result.append(
                    XenVM(
                        uuid=rec.get("uuid", ""),
                        name_label=rec.get("name_label", ""),
                        power_state=rec.get("power_state", ""),
                        memory_static_max=int(rec.get("memory_static_max", 0)),
                        vcpus_max=int(rec.get("VCPUs_max", 0)),
                        resident_on=rec.get("resident_on", ""),
                    )
                )
            return result
        except AttributeError as exc:
            log.error("xenserver list_vms: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("xenserver list_vms failed", error=str(exc))
            return []

    def get_vm_snapshots(self, vm_uuid: str) -> list[XenSnapshot]:
        """Return all snapshots for a given VM UUID."""
        try:
            if self._session is None:
                raise AttributeError("not connected")
            vm_ref = self._xe.VM.get_by_uuid(vm_uuid)
            snap_refs = self._xe.VM.get_snapshots(vm_ref)
            result = []
            for snap_ref in snap_refs:
                rec = self._xe.VM.get_record(snap_ref)
                result.append(
                    XenSnapshot(
                        uuid=rec.get("uuid", ""),
                        name_label=rec.get("name_label", ""),
                        name_description=rec.get("name_description", ""),
                        snapshot_time=str(rec.get("snapshot_time", "")),
                        snapshot_of=rec.get("snapshot_of", ""),
                    )
                )
            return result
        except AttributeError as exc:
            log.error("xenserver get_vm_snapshots: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("xenserver get_vm_snapshots failed", vm_uuid=vm_uuid, error=str(exc))
            return []

    def create_snapshot(self, vm_uuid: str, name: str) -> str:
        """Create a snapshot of the given VM. Returns the new snapshot UUID."""
        try:
            if self._session is None:
                raise AttributeError("not connected")
            vm_ref = self._xe.VM.get_by_uuid(vm_uuid)
            snap_ref = self._xe.VM.snapshot(vm_ref, name)
            return self._xe.VM.get_uuid(snap_ref)
        except AttributeError as exc:
            log.error("xenserver create_snapshot: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error("xenserver create_snapshot failed", vm_uuid=vm_uuid, error=str(exc))
            return ""

    def restore_vm_from_snapshot(self, snapshot_uuid: str, new_vm_name: str) -> str:
        """Clone a snapshot into a new VM. Returns the new VM UUID."""
        try:
            if self._session is None:
                raise AttributeError("not connected")
            snap_ref = self._xe.VM.get_by_uuid(snapshot_uuid)
            new_vm_ref = self._xe.VM.clone(snap_ref, new_vm_name)
            return self._xe.VM.get_uuid(new_vm_ref)
        except AttributeError as exc:
            log.error("xenserver restore_vm_from_snapshot: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error(
                "xenserver restore_vm_from_snapshot failed",
                snapshot_uuid=snapshot_uuid,
                error=str(exc),
            )
            return ""

    def get_task_status(self, task_uuid: str) -> XenTask:
        """Return the status of a XenAPI task."""
        try:
            if self._session is None:
                raise AttributeError("not connected")
            task_ref = self._xe.task.get_by_uuid(task_uuid)
            rec = self._xe.task.get_record(task_ref)
            return XenTask(
                uuid=task_uuid,
                status=rec.get("status", ""),
                progress=float(rec.get("progress", 0.0)),
                result=rec.get("result", ""),
            )
        except AttributeError as exc:
            log.error("xenserver get_task_status: not connected", error=str(exc))
            return XenTask(uuid=task_uuid, status="error", progress=0.0, result="")
        except Exception as exc:
            log.error("xenserver get_task_status failed", task_uuid=task_uuid, error=str(exc))
            return XenTask(uuid=task_uuid, status="error", progress=0.0, result="")

    def get_vm_health(self, vm_uuid: str) -> dict:
        """Return basic health info for a VM."""
        try:
            if self._session is None:
                raise AttributeError("not connected")
            vm_ref = self._xe.VM.get_by_uuid(vm_uuid)
            rec = self._xe.VM.get_record(vm_ref)
            return {
                "power_state": rec.get("power_state", ""),
                "name_label": rec.get("name_label", ""),
            }
        except AttributeError as exc:
            log.error("xenserver get_vm_health: not connected", error=str(exc))
            return {}
        except Exception as exc:
            log.error("xenserver get_vm_health failed", vm_uuid=vm_uuid, error=str(exc))
            return {}

    def delete_snapshot(self, snapshot_uuid: str) -> bool:
        """Destroy a snapshot VM record. Returns True on success."""
        try:
            if self._session is None:
                raise AttributeError("not connected")
            snap_ref = self._xe.VM.get_by_uuid(snapshot_uuid)
            self._xe.VM.destroy(snap_ref)
            return True
        except AttributeError as exc:
            log.error("xenserver delete_snapshot: not connected", error=str(exc))
            return False
        except Exception as exc:
            log.error(
                "xenserver delete_snapshot failed",
                snapshot_uuid=snapshot_uuid,
                error=str(exc),
            )
            return False
