"""Red Hat Virtualization (RHV) / oVirt connector.

Uses the oVirt Engine Python SDK to manage VMs, snapshots, and restore operations.
Supports RHV 4.x and upstream oVirt installations.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

from src.config import settings

log = structlog.get_logger()


@dataclass
class RHVVm:
    id: str
    name: str
    status: str
    memory: int
    cpu_cores: int
    cluster_id: str
    template_id: str | None


@dataclass
class RHVSnapshot:
    id: str
    description: str
    vm_id: str
    date: str
    snapshot_type: str
    persist_memorystate: bool


@dataclass
class RHVDisk:
    id: str
    alias: str
    actual_size: int
    status: str


class RHVClient:
    """Client for Red Hat Virtualization via the oVirt Engine Python SDK."""

    def __init__(self) -> None:
        self._conn = None

    def connect(self) -> bool:
        """Connect to the RHV/oVirt Engine. Returns True on success."""
        try:
            import ovirtsdk4 as sdk  # type: ignore
        except ImportError:
            log.warning(
                "ovirtsdk4 not installed, run: pip install ovirt-engine-sdk-python"
            )
            return False
        try:
            kwargs: dict = {
                "url": settings.rhv_url,
                "username": settings.rhv_username,
                "password": settings.rhv_password.get_secret_value(),
                "insecure": settings.rhv_ca_file == "",
            }
            if settings.rhv_ca_file:
                kwargs["ca_file"] = settings.rhv_ca_file
            self._conn = sdk.Connection(**kwargs)
            return True
        except Exception as exc:
            log.error("rhv connect failed", error=str(exc))
            return False

    def list_vms(self) -> list[RHVVm]:
        """Return all VMs from the RHV Engine."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            vms_service = self._conn.system_service().vms_service()
            result = []
            for vm in vms_service.list():
                cluster_id = vm.cluster.id if vm.cluster else ""
                template_id = vm.template.id if vm.template else None
                cpu_cores = 0
                if vm.cpu and vm.cpu.topology:
                    cpu_cores = (
                        (vm.cpu.topology.cores or 1)
                        * (vm.cpu.topology.sockets or 1)
                        * (vm.cpu.topology.threads or 1)
                    )
                result.append(
                    RHVVm(
                        id=vm.id or "",
                        name=vm.name or "",
                        status=str(vm.status) if vm.status else "",
                        memory=int(vm.memory) if vm.memory else 0,
                        cpu_cores=cpu_cores,
                        cluster_id=cluster_id,
                        template_id=template_id,
                    )
                )
            return result
        except AttributeError as exc:
            log.error("rhv list_vms: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("rhv list_vms failed", error=str(exc))
            return []

    def get_vm_snapshots(self, vm_id: str) -> list[RHVSnapshot]:
        """Return all snapshots for a given VM ID."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            vms_service = self._conn.system_service().vms_service()
            snaps_service = vms_service.vm_service(vm_id).snapshots_service()
            result = []
            for snap in snaps_service.list():
                result.append(
                    RHVSnapshot(
                        id=snap.id or "",
                        description=snap.description or "",
                        vm_id=vm_id,
                        date=str(snap.date) if snap.date else "",
                        snapshot_type=str(snap.snapshot_type) if snap.snapshot_type else "",
                        persist_memorystate=bool(snap.persist_memorystate),
                    )
                )
            return result
        except AttributeError as exc:
            log.error("rhv get_vm_snapshots: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("rhv get_vm_snapshots failed", vm_id=vm_id, error=str(exc))
            return []

    def create_snapshot(self, vm_id: str, description: str) -> str:
        """Create a snapshot of the given VM. Returns the snapshot ID."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            import ovirtsdk4.types as types  # type: ignore
            vms_service = self._conn.system_service().vms_service()
            snaps_service = vms_service.vm_service(vm_id).snapshots_service()
            snap = snaps_service.add(types.Snapshot(description=description))
            return snap.id or ""
        except AttributeError as exc:
            log.error("rhv create_snapshot: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error("rhv create_snapshot failed", vm_id=vm_id, error=str(exc))
            return ""

    def restore_vm_from_snapshot(self, vm_id: str, snapshot_id: str) -> bool:
        """Preview then commit a snapshot rollback. Returns True on success."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            vms_service = self._conn.system_service().vms_service()
            vm_service = vms_service.vm_service(vm_id)
            snaps_service = vm_service.snapshots_service()
            snap_service = snaps_service.snapshot_service(snapshot_id)
            snap_service.restore(restore_memory=False)
            vm_service.commit_snapshot()
            return True
        except AttributeError as exc:
            log.error("rhv restore_vm_from_snapshot: not connected", error=str(exc))
            return False
        except Exception as exc:
            log.error(
                "rhv restore_vm_from_snapshot failed",
                vm_id=vm_id,
                snapshot_id=snapshot_id,
                error=str(exc),
            )
            return False

    def get_vm_health(self, vm_id: str) -> dict:
        """Return basic health info for a VM."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            vms_service = self._conn.system_service().vms_service()
            vm = vms_service.vm_service(vm_id).get()
            return {
                "status": str(vm.status) if vm.status else "",
                "name": vm.name or "",
            }
        except AttributeError as exc:
            log.error("rhv get_vm_health: not connected", error=str(exc))
            return {}
        except Exception as exc:
            log.error("rhv get_vm_health failed", vm_id=vm_id, error=str(exc))
            return {}

    def list_vm_disks(self, vm_id: str) -> list[RHVDisk]:
        """Return disk attachments for a given VM ID."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            vms_service = self._conn.system_service().vms_service()
            das_service = vms_service.vm_service(vm_id).disk_attachments_service()
            result = []
            for da in das_service.list():
                disk = da.disk
                result.append(
                    RHVDisk(
                        id=disk.id or "" if disk else "",
                        alias=disk.alias or "" if disk else "",
                        actual_size=int(disk.actual_size) if disk and disk.actual_size else 0,
                        status=str(disk.status) if disk and disk.status else "",
                    )
                )
            return result
        except AttributeError as exc:
            log.error("rhv list_vm_disks: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("rhv list_vm_disks failed", vm_id=vm_id, error=str(exc))
            return []

    def start_vm(self, vm_id: str) -> bool:
        """Start a VM. Returns True on success."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            vms_service = self._conn.system_service().vms_service()
            vms_service.vm_service(vm_id).start()
            return True
        except AttributeError as exc:
            log.error("rhv start_vm: not connected", error=str(exc))
            return False
        except Exception as exc:
            log.error("rhv start_vm failed", vm_id=vm_id, error=str(exc))
            return False

    def stop_vm(self, vm_id: str) -> bool:
        """Stop a VM. Returns True on success."""
        try:
            if self._conn is None:
                raise AttributeError("not connected")
            vms_service = self._conn.system_service().vms_service()
            vms_service.vm_service(vm_id).stop()
            return True
        except AttributeError as exc:
            log.error("rhv stop_vm: not connected", error=str(exc))
            return False
        except Exception as exc:
            log.error("rhv stop_vm failed", vm_id=vm_id, error=str(exc))
            return False
