"""
Hyper-V connector for R3VP.

Uses Windows Management Instrumentation (WMI) via pywin32 to:
- List Hyper-V VMs and their current state
- Create isolated virtual switches for sandbox testing
- Trigger VM checkpoints (snapshots) for instant-style recovery tests
- Check VM health post-recovery via WMI

This connector only works when the appliance is running on a Windows host
with Hyper-V enabled. It gracefully reports unavailable on Linux.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import asyncio
import socket
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class HyperVVM:
    vm_id: str
    name: str
    state: str          # "Running", "Off", "Saved", "Paused"
    cpu_count: int = 0
    memory_mb: int = 0
    generation: int = 1
    checkpoint_count: int = 0
    notes: str = ""


@dataclass
class HyperVCheckpoint:
    checkpoint_id: str
    vm_id: str
    name: str
    creation_time: datetime
    snapshot_type: str = "Standard"  # "Standard", "Production"


@dataclass
class HyperVSwitch:
    switch_id: str
    name: str
    switch_type: str  # "Internal", "Private", "External"
    notes: str = ""


def _is_hyperv_available() -> bool:
    """Return True if we are on Windows with pywin32 available."""
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


class HyperVClient:
    """
    Client for the local Hyper-V host via WMI.

    Call `connect()` before using any other methods.
    Only functional on Windows with the Hyper-V role installed.
    """

    def __init__(self, host: str = "localhost") -> None:
        self._host = host
        self._wmi: Any = None
        self._available = _is_hyperv_available()

    def connect(self) -> bool:
        """Connect to the Hyper-V WMI namespace. Returns True on success."""
        if not self._available:
            log.warning("hyperv.unavailable", reason="pywin32 not installed or not on Windows")
            return False
        try:
            import win32com.client
            self._wmi = win32com.client.GetObject(
                f"winmgmts:\\\\{self._host}\\root\\virtualization\\v2"
            )
            log.info("hyperv.connected", host=self._host)
            return True
        except Exception as exc:
            log.error("hyperv.connect_failed", error=str(exc))
            return False

    def list_vms(self) -> list[HyperVVM]:
        """List all VMs on this Hyper-V host."""
        if not self._wmi:
            return []
        try:
            vms = self._wmi.ExecQuery(
                "SELECT * FROM Msvm_ComputerSystem WHERE Caption = 'Virtual Machine'"
            )
            result = []
            for vm in vms:
                state_map = {
                    0: "Unknown", 2: "Running", 3: "Off", 6: "Paused", 9: "Saved",
                    10: "Starting", 11: "Snapshotting", 32768: "Pausing", 32769: "Resuming",
                }
                state = state_map.get(vm.EnabledState, "Unknown")
                result.append(
                    HyperVVM(
                        vm_id=vm.Name,
                        name=vm.ElementName,
                        state=state,
                        notes=vm.Description or "",
                    )
                )
            return result
        except Exception as exc:
            log.error("hyperv.list_vms_failed", error=str(exc))
            return []

    def get_vm_checkpoints(self, vm_id: str) -> list[HyperVCheckpoint]:
        """List all checkpoints for a VM."""
        if not self._wmi:
            return []
        try:
            snaps = self._wmi.ExecQuery(
                f"SELECT * FROM Msvm_VirtualSystemSettingData WHERE VirtualSystemType = 'Microsoft:Hyper-V:Snapshot:Realized' AND SystemName = '{vm_id}'"
            )
            result = []
            for snap in snaps:
                creation_str = snap.CreationTime or ""
                try:
                    # WMI datetime: yyyymmddHHMMSS.ffffff+UUU
                    creation_dt = datetime.strptime(creation_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    creation_dt = datetime.now(timezone.utc)
                result.append(
                    HyperVCheckpoint(
                        checkpoint_id=snap.InstanceID,
                        vm_id=vm_id,
                        name=snap.ElementName or "Checkpoint",
                        creation_time=creation_dt,
                        snapshot_type=snap.VirtualSystemType or "Standard",
                    )
                )
            return result
        except Exception as exc:
            log.error("hyperv.get_checkpoints_failed", vm_id=vm_id, error=str(exc))
            return []

    def create_checkpoint(self, vm_id: str, checkpoint_name: str | None = None) -> str | None:
        """Create a checkpoint of the VM. Returns checkpoint ID on success."""
        if not self._wmi:
            return None
        try:
            name = checkpoint_name or f"R3VP-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            svc = self._wmi.ExecQuery(
                "SELECT * FROM Msvm_VirtualSystemSnapshotService"
            )[0]
            vm_setting = self._wmi.ExecQuery(
                f"SELECT * FROM Msvm_VirtualSystemSettingData WHERE VirtualSystemType = 'Microsoft:Hyper-V:System:Realized' AND SystemName = '{vm_id}'"
            )[0]
            result, snap_path, job_path = svc.CreateSnapshot(
                AffectedSystem=vm_setting.path_(),
                SnapshotSettings="",
                SnapshotType=2,  # 2 = Recovery (production checkpoint)
            )
            if result == 0:
                log.info("hyperv.checkpoint_created", vm_id=vm_id, name=name)
                return snap_path
            log.error("hyperv.checkpoint_failed", vm_id=vm_id, result=result)
            return None
        except Exception as exc:
            log.error("hyperv.checkpoint_failed", vm_id=vm_id, error=str(exc))
            return None

    def restore_vm_from_checkpoint(self, vm_id: str, checkpoint_id: str) -> bool:
        """Restore VM to a checkpoint state (stops VM first)."""
        if not self._wmi:
            return False
        try:
            svc = self._wmi.ExecQuery(
                "SELECT * FROM Msvm_VirtualSystemSnapshotService"
            )[0]
            snap = self._wmi.ExecQuery(
                f"SELECT * FROM Msvm_VirtualSystemSettingData WHERE InstanceID = '{checkpoint_id}'"
            )[0]
            result, job_path = svc.ApplySnapshot(SnapshotSettings=snap.path_())
            log.info("hyperv.restore_complete", vm_id=vm_id, result=result)
            return result == 0
        except Exception as exc:
            log.error("hyperv.restore_failed", vm_id=vm_id, error=str(exc))
            return False

    def create_internal_switch(self, switch_name: str) -> HyperVSwitch | None:
        """Create a new internal virtual switch for isolated test networking."""
        if not self._wmi:
            return None
        try:
            svc = self._wmi.ExecQuery(
                "SELECT * FROM Msvm_VirtualEthernetSwitchManagementService"
            )[0]
            switch_settings_class = self._wmi.Get("Msvm_VirtualEthernetSwitchSettingData")
            switch_settings = switch_settings_class.SpawnInstance_()
            switch_settings.ElementName = switch_name
            switch_id = str(uuid.uuid4())
            result, new_switch, job_path = svc.DefineSystem(
                SystemSettings=switch_settings.GetText_(1),
                ResourceSettings=[],
                ReferenceConfiguration=None,
            )
            if result == 0:
                log.info("hyperv.switch_created", name=switch_name)
                return HyperVSwitch(
                    switch_id=switch_id,
                    name=switch_name,
                    switch_type="Internal",
                    notes="Created by R3VP for isolation testing",
                )
            return None
        except Exception as exc:
            log.error("hyperv.switch_create_failed", name=switch_name, error=str(exc))
            return None

    def delete_switch(self, switch_name: str) -> bool:
        """Delete an internal switch created by R3VP (teardown)."""
        if not self._wmi:
            return False
        try:
            svc = self._wmi.ExecQuery(
                "SELECT * FROM Msvm_VirtualEthernetSwitchManagementService"
            )[0]
            switches = self._wmi.ExecQuery(
                f"SELECT * FROM Msvm_VirtualEthernetSwitch WHERE ElementName = '{switch_name}'"
            )
            for sw in switches:
                result, job_path = svc.DestroySystem(AffectedSystem=sw.path_())
                if result == 0:
                    log.info("hyperv.switch_deleted", name=switch_name)
                    return True
            return False
        except Exception as exc:
            log.error("hyperv.switch_delete_failed", name=switch_name, error=str(exc))
            return False

    def get_vm_health(self, vm_id: str) -> dict:
        """Check VM health indicators via WMI."""
        if not self._wmi:
            return {"available": False}
        try:
            vms = self._wmi.ExecQuery(
                f"SELECT * FROM Msvm_ComputerSystem WHERE Name = '{vm_id}'"
            )
            for vm in vms:
                return {
                    "available": True,
                    "name": vm.ElementName,
                    "state": vm.EnabledState,
                    "health_state": vm.HealthState,  # 5=OK, 20=Major, 25=Critical
                    "operational_status": list(vm.OperationalStatus or []),
                }
            return {"available": False, "reason": "VM not found"}
        except Exception as exc:
            return {"available": False, "reason": str(exc)}
