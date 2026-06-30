"""Proxmox VE connector for backup and recovery validation.

Uses proxmoxer to communicate with the Proxmox VE REST API.
Supports VM snapshot creation, restore, and Proxmox Backup Server (PBS) integration.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

from src.config import settings

log = structlog.get_logger()


@dataclass
class ProxmoxVM:
    vmid: int
    name: str
    node: str
    status: str
    maxmem: int
    maxcpu: int
    uptime: int


@dataclass
class ProxmoxSnapshot:
    vmid: int
    name: str
    description: str
    snaptime: int
    parent: str | None


@dataclass
class ProxmoxBackupJob:
    id: str
    node: str
    storage: str
    vmid: int
    starttime: int
    endtime: int
    status: str


class ProxmoxClient:
    """Client for Proxmox VE via the proxmoxer library."""

    def __init__(self) -> None:
        self._proxmox = None
        self._node = settings.proxmox_node

    def connect(self) -> bool:
        """Connect to Proxmox VE. Returns True on success."""
        try:
            from proxmoxer import ProxmoxAPI  # type: ignore
        except ImportError:
            log.warning("proxmoxer not installed, run: pip install proxmoxer requests")
            return False
        try:
            self._proxmox = ProxmoxAPI(
                settings.proxmox_host,
                user=settings.proxmox_user,
                password=settings.proxmox_password.get_secret_value(),
                backend="https",
                verify_ssl=settings.proxmox_verify_ssl,
            )
            return True
        except Exception as exc:
            log.error("proxmox connect failed", error=str(exc))
            return False

    def list_vms(self) -> list[ProxmoxVM]:
        """Return all QEMU VMs on the configured node."""
        try:
            if self._proxmox is None:
                raise AttributeError("not connected")
            raw = self._proxmox.nodes(self._node).qemu.get()
            return [
                ProxmoxVM(
                    vmid=int(vm.get("vmid", 0)),
                    name=vm.get("name", ""),
                    node=self._node,
                    status=vm.get("status", ""),
                    maxmem=int(vm.get("maxmem", 0)),
                    maxcpu=int(vm.get("maxcpu", 0)),
                    uptime=int(vm.get("uptime", 0)),
                )
                for vm in raw
            ]
        except AttributeError as exc:
            log.error("proxmox list_vms: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("proxmox list_vms failed", error=str(exc))
            return []

    def get_vm_snapshots(self, vmid: int) -> list[ProxmoxSnapshot]:
        """Return snapshots for a given VM."""
        try:
            if self._proxmox is None:
                raise AttributeError("not connected")
            raw = self._proxmox.nodes(self._node).qemu(vmid).snapshot.get()
            return [
                ProxmoxSnapshot(
                    vmid=vmid,
                    name=s.get("name", ""),
                    description=s.get("description", ""),
                    snaptime=int(s.get("snaptime", 0)),
                    parent=s.get("parent"),
                )
                for s in raw
            ]
        except AttributeError as exc:
            log.error("proxmox get_vm_snapshots: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("proxmox get_vm_snapshots failed", vmid=vmid, error=str(exc))
            return []

    def create_snapshot(self, vmid: int, name: str, description: str = "") -> str:
        """Create a snapshot and return the task UPID."""
        try:
            if self._proxmox is None:
                raise AttributeError("not connected")
            upid = self._proxmox.nodes(self._node).qemu(vmid).snapshot.post(
                snapname=name,
                description=description,
            )
            return upid
        except AttributeError as exc:
            log.error("proxmox create_snapshot: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error("proxmox create_snapshot failed", vmid=vmid, name=name, error=str(exc))
            return ""

    def restore_vm_from_snapshot(self, vmid: int, snapshot_name: str) -> bool:
        """Roll back a VM to a named snapshot. Returns True on success."""
        try:
            if self._proxmox is None:
                raise AttributeError("not connected")
            self._proxmox.nodes(self._node).qemu(vmid).snapshot(snapshot_name).rollback.post()
            return True
        except AttributeError as exc:
            log.error("proxmox restore_vm_from_snapshot: not connected", error=str(exc))
            return False
        except Exception as exc:
            log.error(
                "proxmox restore_vm_from_snapshot failed",
                vmid=vmid,
                snapshot_name=snapshot_name,
                error=str(exc),
            )
            return False

    def list_backup_jobs(self) -> list[ProxmoxBackupJob]:
        """Return recent vzdump backup tasks on the configured node."""
        try:
            if self._proxmox is None:
                raise AttributeError("not connected")
            raw = self._proxmox.nodes(self._node).tasks.get(typefilter="vzdump")
            return [
                ProxmoxBackupJob(
                    id=t.get("upid", ""),
                    node=self._node,
                    storage="",
                    vmid=int(t.get("id", 0)) if str(t.get("id", "")).isdigit() else 0,
                    starttime=int(t.get("starttime", 0)),
                    endtime=int(t.get("endtime", 0)),
                    status=t.get("status", ""),
                )
                for t in raw
            ]
        except AttributeError as exc:
            log.error("proxmox list_backup_jobs: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("proxmox list_backup_jobs failed", error=str(exc))
            return []

    def get_vm_health(self, vmid: int) -> dict:
        """Return basic health info for a VM."""
        try:
            if self._proxmox is None:
                raise AttributeError("not connected")
            data = self._proxmox.nodes(self._node).qemu(vmid).status.current.get()
            return {
                "status": data.get("status", ""),
                "uptime": data.get("uptime", 0),
                "cpu": data.get("cpu", 0.0),
                "mem": data.get("mem", 0),
            }
        except AttributeError as exc:
            log.error("proxmox get_vm_health: not connected", error=str(exc))
            return {}
        except Exception as exc:
            log.error("proxmox get_vm_health failed", vmid=vmid, error=str(exc))
            return {}

    def delete_snapshot(self, vmid: int, snapshot_name: str) -> bool:
        """Delete a named snapshot. Returns True on success."""
        try:
            if self._proxmox is None:
                raise AttributeError("not connected")
            self._proxmox.nodes(self._node).qemu(vmid).snapshot(snapshot_name).delete()
            return True
        except AttributeError as exc:
            log.error("proxmox delete_snapshot: not connected", error=str(exc))
            return False
        except Exception as exc:
            log.error(
                "proxmox delete_snapshot failed",
                vmid=vmid,
                snapshot_name=snapshot_name,
                error=str(exc),
            )
            return False
