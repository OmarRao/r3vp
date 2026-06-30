"""
Veeam B&R REST API data models.

Supports Veeam 11 (v1.0), 12 (v1.1), and 13.0.2+ (v1.2).

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VeeamJob(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str
    type: str = ""
    description: str = ""
    is_enabled: bool = Field(default=True, alias="isEnabled")
    last_run: datetime | None = Field(default=None, alias="lastRun")
    status: str = ""


class VeeamVM(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    objectId: str
    name: str
    platform: str = "vmware"
    osType: str | None = None
    isProtected: bool = True
    backupJobsCount: int = 0
    restore_points_count: int = Field(default=0, alias="restorePointsCount")

    # Keep legacy aliases so existing code calling vm.object_id / vm.last_backup still works
    @property
    def object_id(self) -> str:
        return self.objectId

    @property
    def last_backup(self) -> None:
        return None


class VeeamRestorePoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    name: str = ""
    creationTime: datetime
    objectId: str = ""
    backupSize: int = 0
    is_consistent: bool = Field(default=True, alias="isConsistent")
    backup_size_bytes: int = Field(default=0, alias="backupSizeBytes")

    # Legacy alias used by existing activities
    @property
    def creation_time(self) -> datetime:
        return self.creationTime


class VeeamRepository(BaseModel):
    id: str
    name: str
    type: str = ""
    capacity: int = 0
    freeSpace: int = 0
    path: str = ""


class VeeamMalwareEvent(BaseModel):
    """Inline malware detection event from Veeam 13's built-in scanner."""
    id: str
    detectionTime: datetime
    machineId: str = ""
    machineName: str = ""
    eventType: str = ""       # e.g. "SuspiciousActivity", "MalwareDetected"
    severity: str = "Unknown" # "High", "Medium", "Low", "Unknown"
    details: str = ""
    isResolved: bool = False


class VeeamJobSession(BaseModel):
    id: str
    jobId: str = ""
    creationTime: datetime
    endTime: datetime | None = None
    state: str = "Running"    # "Running", "Stopped", "Failed", "Success"
    result: str = "None"      # "None", "Success", "Warning", "Failed"
    progress: int = 0
