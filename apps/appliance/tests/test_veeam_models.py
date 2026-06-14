"""Unit tests for Veeam connector models — no network required."""
from datetime import datetime, timezone
from src.connectors.veeam.models import VeeamJob, VeeamVM, VeeamRestorePoint


def test_veeam_job_parses_alias() -> None:
    job = VeeamJob.model_validate({
        "id": "abc123",
        "name": "Daily Backup",
        "type": "Backup",
        "isEnabled": True,
        "lastRun": "2026-06-01T02:00:00Z",
        "status": "Success",
    })
    assert job.id == "abc123"
    assert job.is_enabled is True
    assert job.last_run is not None


def test_veeam_vm_defaults() -> None:
    vm = VeeamVM.model_validate({
        "objectId": "vm-001",
        "name": "web-server-01",
        "platform": "VMware",
        "jobId": "job-001",
    })
    assert vm.restore_points_count == 0
    assert vm.last_backup is None


def test_restore_point_parses() -> None:
    rp = VeeamRestorePoint.model_validate({
        "id": "rp-001",
        "creationTime": "2026-06-14T01:00:00+00:00",
        "objectId": "vm-001",
        "isConsistent": True,
        "backupSizeBytes": 10_000_000,
    })
    assert rp.is_consistent is True
    assert rp.backup_size_bytes == 10_000_000
