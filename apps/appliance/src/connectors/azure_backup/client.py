"""
Azure Backup connector for R3VP.

Authenticates via Azure Managed Identity or service principal (MSAL/azure-identity)
and provides methods to list Recovery Services Vaults, protected VMs, recovery points,
trigger test restores to an isolated resource group, and check VM health.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class AzureVault:
    vault_id: str
    vault_name: str
    resource_group: str
    location: str
    subscription_id: str


@dataclass
class AzureProtectedItem:
    item_id: str
    friendly_name: str
    vault_name: str
    resource_group: str
    workload_type: str = "VM"         # "VM", "SQLDataBase", "AzureFileShare"
    protection_status: str = "Healthy"
    last_backup_time: datetime | None = None


@dataclass
class AzureRecoveryPoint:
    recovery_point_id: str
    recovery_point_time: datetime
    recovery_point_type: str = "Full"  # "Full", "Differential", "Incremental"
    item_name: str = ""
    vault_name: str = ""
    resource_group: str = ""


@dataclass
class AzureRestoreJob:
    job_id: str
    operation: str = "Restore"
    status: str = "InProgress"   # "InProgress", "Completed", "Failed", "Cancelled"
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    restored_vm_name: str = ""


def _try_import_azure() -> tuple[Any, Any, bool]:
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
        return DefaultAzureCredential, RecoveryServicesBackupClient, True
    except ImportError:
        return None, None, False


class AzureBackupClient:
    """
    Client for Azure Backup (Recovery Services Vault).

    Requires azure-identity and azure-mgmt-recoveryservicesbackup.
    Uses DefaultAzureCredential (tries managed identity, then env vars, then CLI).
    """

    def __init__(self, subscription_id: str, tenant_id: str = "") -> None:
        self._subscription_id = subscription_id
        self._tenant_id = tenant_id
        self._credential: Any = None
        self._backup_client: Any = None
        DefaultAzureCredential, RecoveryServicesBackupClient, self._available = _try_import_azure()
        self._DefaultAzureCredential = DefaultAzureCredential
        self._RecoveryServicesBackupClient = RecoveryServicesBackupClient

    def connect(self) -> bool:
        """Initialise Azure clients. Returns True on success."""
        if not self._available:
            log.warning("azure_backup.unavailable", reason="azure-identity or azure-mgmt-recoveryservicesbackup not installed")
            return False
        try:
            self._credential = self._DefaultAzureCredential()
            self._backup_client = self._RecoveryServicesBackupClient(
                credential=self._credential,
                subscription_id=self._subscription_id,
            )
            log.info("azure_backup.connected", subscription=self._subscription_id)
            return True
        except Exception as exc:
            log.error("azure_backup.connect_failed", error=str(exc))
            return False

    def list_protected_vms(
        self, vault_name: str, resource_group: str
    ) -> list[AzureProtectedItem]:
        """List VMs protected by a Recovery Services Vault."""
        if not self._backup_client:
            return []
        try:
            items = self._backup_client.backup_protected_items.list(
                vault_name=vault_name,
                resource_group_name=resource_group,
                filter="backupManagementType eq 'AzureIaasVM'",
            )
            result = []
            for item in items:
                props = item.properties
                last_backup = getattr(props, "last_backup_time", None)
                result.append(
                    AzureProtectedItem(
                        item_id=item.id or "",
                        friendly_name=getattr(props, "friendly_name", item.name or ""),
                        vault_name=vault_name,
                        resource_group=resource_group,
                        workload_type="VM",
                        protection_status=getattr(props, "health_status", "Healthy"),
                        last_backup_time=last_backup,
                    )
                )
            return result
        except Exception as exc:
            log.error("azure_backup.list_vms_failed", vault=vault_name, error=str(exc))
            return []

    def list_recovery_points(
        self,
        vault_name: str,
        resource_group: str,
        container_name: str,
        protected_item_name: str,
    ) -> list[AzureRecoveryPoint]:
        """List recovery points for a protected VM."""
        if not self._backup_client:
            return []
        try:
            rps = self._backup_client.recovery_points.list(
                vault_name=vault_name,
                resource_group_name=resource_group,
                fabric_name="Azure",
                container_name=container_name,
                protected_item_name=protected_item_name,
            )
            result = []
            for rp in rps:
                props = rp.properties
                rp_time = getattr(props, "recovery_point_time", datetime.now(UTC))
                rp_type = getattr(props, "recovery_point_type", "Full")
                result.append(
                    AzureRecoveryPoint(
                        recovery_point_id=rp.name or "",
                        recovery_point_time=rp_time,
                        recovery_point_type=rp_type,
                        item_name=protected_item_name,
                        vault_name=vault_name,
                        resource_group=resource_group,
                    )
                )
            return result
        except Exception as exc:
            log.error("azure_backup.list_rps_failed", vault=vault_name, error=str(exc))
            return []

    def restore_vm(
        self,
        vault_name: str,
        resource_group: str,
        container_name: str,
        protected_item_name: str,
        recovery_point_id: str,
        target_resource_group: str,
        target_vm_name: str,
        target_vnet_id: str,
        target_subnet_name: str,
    ) -> AzureRestoreJob | None:
        """
        Restore a VM to an isolated resource group for testing.

        The target_resource_group and target_vnet_id should point to a
        dedicated isolated environment with no peering to production networks.
        """
        if not self._backup_client:
            return None
        try:
            from azure.mgmt.recoveryservicesbackup.models import (
                IaasVMRestoreRequest,
                TriggerRestoreRequest,
            )
            restore_request = TriggerRestoreRequest(
                properties=IaasVMRestoreRequest(
                    recovery_point_id=recovery_point_id,
                    recovery_type="AlternateLocation",
                    target_resource_group_id=f"/subscriptions/{self._subscription_id}/resourceGroups/{target_resource_group}",
                    storage_account_id=None,
                    target_virtual_machine_id=None,
                    target_virtual_network_id=target_vnet_id,
                    subnet_id=f"{target_vnet_id}/subnets/{target_subnet_name}",
                    target_domain_name_id=None,
                    region=None,
                    create_new_cloud_service=True,
                    original_storage_account_option=False,
                    restore_disk_lun_list=None,
                )
            )
            poller = self._backup_client.restores.begin_trigger(
                vault_name=vault_name,
                resource_group_name=resource_group,
                fabric_name="Azure",
                container_name=container_name,
                protected_item_name=protected_item_name,
                recovery_point_id=recovery_point_id,
                parameters=restore_request,
            )
            log.info("azure_backup.restore_triggered", vm=target_vm_name)
            return AzureRestoreJob(
                job_id=str(poller),
                status="InProgress",
                restored_vm_name=target_vm_name,
            )
        except Exception as exc:
            log.error("azure_backup.restore_failed", error=str(exc))
            return None

    def get_job_status(self, vault_name: str, resource_group: str, job_id: str) -> dict:
        """Get status of a backup or restore job."""
        if not self._backup_client:
            return {"status": "Unknown"}
        try:
            job = self._backup_client.jobs.get(
                vault_name=vault_name,
                resource_group_name=resource_group,
                job_name=job_id,
            )
            props = job.properties
            return {
                "status": getattr(props, "status", "Unknown"),
                "operation": getattr(props, "operation", ""),
                "start_time": getattr(props, "start_time", None),
                "end_time": getattr(props, "end_time", None),
                "error_details": getattr(props, "error_details", None),
            }
        except Exception as exc:
            return {"status": "Unknown", "error": str(exc)}
