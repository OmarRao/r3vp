"""Google Cloud Platform (GCP) Backup and DR connector.

Uses google-cloud-compute for snapshot operations and google-cloud-backupdr
for Backup and DR Service vault management.
Authenticates via Application Default Credentials (service account, metadata server, or gcloud CLI).

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from dataclasses import dataclass, field
import structlog

from src.config import settings

log = structlog.get_logger()


@dataclass
class GCPInstance:
    id: str
    name: str
    zone: str
    status: str
    machine_type: str
    network_interfaces: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class GCPSnapshot:
    id: str
    name: str
    source_disk: str
    zone: str
    status: str
    creation_timestamp: str
    disk_size_gb: int


@dataclass
class GCPRestoreJob:
    operation_id: str
    status: str
    zone: str
    target_instance: str
    started_at: str


class GCPBackupClient:
    """Client for GCP Compute Engine snapshot operations and instance management."""

    def __init__(self) -> None:
        self._instances_client = None
        self._snapshots_client = None
        self._credentials = None

    def connect(self) -> bool:
        """Initialize GCP clients. Returns True on success."""
        try:
            import google.cloud.compute_v1 as compute_v1  # type: ignore
            import google.auth  # type: ignore
        except ImportError:
            log.warning(
                "google-cloud-compute not installed, run: pip install google-cloud-compute"
            )
            return False
        try:
            if settings.gcp_service_account_json:
                from google.oauth2 import service_account  # type: ignore
                credentials = service_account.Credentials.from_service_account_file(
                    settings.gcp_service_account_json,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            else:
                credentials, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            self._credentials = credentials
            self._instances_client = compute_v1.InstancesClient(credentials=credentials)
            self._snapshots_client = compute_v1.SnapshotsClient(credentials=credentials)
            return True
        except Exception as exc:
            log.error("gcp connect failed", error=str(exc))
            return False

    def list_instances(self) -> list[GCPInstance]:
        """Return all instances in the configured project and zone."""
        try:
            if self._instances_client is None:
                raise AttributeError("not connected")
            result = []
            for inst in self._instances_client.list(
                project=settings.gcp_project_id,
                zone=settings.gcp_zone,
            ):
                nis = [ni.network for ni in (inst.network_interfaces or [])]
                machine_type = inst.machine_type or ""
                if "/" in machine_type:
                    machine_type = machine_type.rsplit("/", 1)[-1]
                result.append(
                    GCPInstance(
                        id=str(inst.id) if inst.id else "",
                        name=inst.name or "",
                        zone=settings.gcp_zone,
                        status=inst.status or "",
                        machine_type=machine_type,
                        network_interfaces=nis,
                        labels=dict(inst.labels) if inst.labels else {},
                    )
                )
            return result
        except AttributeError as exc:
            log.error("gcp list_instances: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("gcp list_instances failed", error=str(exc))
            return []

    def list_snapshots(self, filter_label: str = "") -> list[GCPSnapshot]:
        """Return snapshots in the configured project, with optional label filter."""
        try:
            if self._snapshots_client is None:
                raise AttributeError("not connected")
            kwargs: dict = {"project": settings.gcp_project_id}
            if filter_label:
                kwargs["filter"] = filter_label
            result = []
            for snap in self._snapshots_client.list(**kwargs):
                source_disk = snap.source_disk or ""
                if "/" in source_disk:
                    source_disk = source_disk.rsplit("/", 1)[-1]
                zone = ""
                if snap.source_disk and "/zones/" in snap.source_disk:
                    zone = snap.source_disk.split("/zones/")[1].split("/")[0]
                result.append(
                    GCPSnapshot(
                        id=str(snap.id) if snap.id else "",
                        name=snap.name or "",
                        source_disk=source_disk,
                        zone=zone,
                        status=snap.status or "",
                        creation_timestamp=snap.creation_timestamp or "",
                        disk_size_gb=int(snap.disk_size_gb) if snap.disk_size_gb else 0,
                    )
                )
            return result
        except AttributeError as exc:
            log.error("gcp list_snapshots: not connected", error=str(exc))
            return []
        except Exception as exc:
            log.error("gcp list_snapshots failed", error=str(exc))
            return []

    def create_snapshot(
        self, instance_name: str, disk_name: str, snapshot_name: str
    ) -> str:
        """Create a snapshot of a disk. Returns the operation name."""
        try:
            if self._instances_client is None:
                raise AttributeError("not connected")
            import google.cloud.compute_v1 as compute_v1  # type: ignore
            disks_client = compute_v1.DisksClient(credentials=self._credentials)
            snapshot_resource = compute_v1.Snapshot(name=snapshot_name)
            operation = disks_client.create_snapshot(
                project=settings.gcp_project_id,
                zone=settings.gcp_zone,
                disk=disk_name,
                snapshot_resource=snapshot_resource,
            )
            return operation.name or ""
        except AttributeError as exc:
            log.error("gcp create_snapshot: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error(
                "gcp create_snapshot failed",
                disk_name=disk_name,
                snapshot_name=snapshot_name,
                error=str(exc),
            )
            return ""

    def restore_instance_from_snapshot(
        self,
        snapshot_name: str,
        new_instance_name: str,
        machine_type: str = "n1-standard-2",
    ) -> GCPRestoreJob:
        """Create a new instance from a snapshot. Returns a GCPRestoreJob."""
        try:
            if self._instances_client is None:
                raise AttributeError("not connected")
            import google.cloud.compute_v1 as compute_v1  # type: ignore
            snapshot_url = (
                f"projects/{settings.gcp_project_id}/global/snapshots/{snapshot_name}"
            )
            machine_type_url = (
                f"zones/{settings.gcp_zone}/machineTypes/{machine_type}"
            )
            boot_disk = compute_v1.AttachedDisk(
                auto_delete=True,
                boot=True,
                initialize_params=compute_v1.AttachedDiskInitializeParams(
                    source_snapshot=snapshot_url,
                ),
            )
            network_interface = compute_v1.NetworkInterface()
            if settings.gcp_target_network:
                network_interface.network = settings.gcp_target_network
            if settings.gcp_target_subnetwork:
                network_interface.subnetwork = settings.gcp_target_subnetwork
            instance = compute_v1.Instance(
                name=new_instance_name,
                machine_type=machine_type_url,
                disks=[boot_disk],
                network_interfaces=[network_interface],
            )
            request = compute_v1.InsertInstanceRequest(
                project=settings.gcp_project_id,
                zone=settings.gcp_zone,
                instance_resource=instance,
            )
            operation = self._instances_client.insert(request=request)
            return GCPRestoreJob(
                operation_id=operation.name or "",
                status=operation.status or "",
                zone=settings.gcp_zone,
                target_instance=new_instance_name,
                started_at=str(operation.insert_time) if hasattr(operation, "insert_time") else "",
            )
        except AttributeError as exc:
            log.error("gcp restore_instance_from_snapshot: not connected", error=str(exc))
            return GCPRestoreJob(
                operation_id="", status="error", zone="", target_instance="", started_at=""
            )
        except Exception as exc:
            log.error(
                "gcp restore_instance_from_snapshot failed",
                snapshot_name=snapshot_name,
                new_instance_name=new_instance_name,
                error=str(exc),
            )
            return GCPRestoreJob(
                operation_id="", status="error", zone="", target_instance="", started_at=""
            )

    def get_operation_status(self, operation_name: str) -> str:
        """Return the status of a zone operation."""
        try:
            if self._instances_client is None:
                raise AttributeError("not connected")
            import google.cloud.compute_v1 as compute_v1  # type: ignore
            ops_client = compute_v1.ZoneOperationsClient(credentials=self._credentials)
            op = ops_client.get(
                project=settings.gcp_project_id,
                zone=settings.gcp_zone,
                operation=operation_name,
            )
            return op.status or ""
        except AttributeError as exc:
            log.error("gcp get_operation_status: not connected", error=str(exc))
            return ""
        except Exception as exc:
            log.error(
                "gcp get_operation_status failed",
                operation_name=operation_name,
                error=str(exc),
            )
            return ""

    def check_instance_health(self, instance_name: str) -> dict:
        """Return basic health info for an instance."""
        try:
            if self._instances_client is None:
                raise AttributeError("not connected")
            inst = self._instances_client.get(
                project=settings.gcp_project_id,
                zone=settings.gcp_zone,
                instance=instance_name,
            )
            return {
                "status": inst.status or "",
                "name": inst.name or "",
                "zone": settings.gcp_zone,
            }
        except AttributeError as exc:
            log.error("gcp check_instance_health: not connected", error=str(exc))
            return {}
        except Exception as exc:
            log.error(
                "gcp check_instance_health failed",
                instance_name=instance_name,
                error=str(exc),
            )
            return {}

    def delete_instance(self, instance_name: str) -> bool:
        """Delete a GCP instance. Returns True on success."""
        try:
            if self._instances_client is None:
                raise AttributeError("not connected")
            self._instances_client.delete(
                project=settings.gcp_project_id,
                zone=settings.gcp_zone,
                instance=instance_name,
            )
            return True
        except AttributeError as exc:
            log.error("gcp delete_instance: not connected", error=str(exc))
            return False
        except Exception as exc:
            log.error("gcp delete_instance failed", instance_name=instance_name, error=str(exc))
            return False
