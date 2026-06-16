"""
Veeam B&R REST API data models.

Supports Veeam 11 (v1.0), 12 (v1.1), and 13.0.2+ (v1.2).

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class VeeamJob(BaseModel):
    id: str
    name: str
    type: str = ""
    isDisabled: bool = False
    description: str = ""


class VeeamVM(BaseModel):
    objectId: str
    name: str
    platform: str = "vmware"
    osType: str | None = None
    isProtected: bool = True
    backupJobsCount: int = 0

    # Keep legacy aliases so existing code calling vm.object_id / vm.last_backup still works
    @property
    def object_id(self) -> str:
        return self.objectId

    @property
    def last_backup(self) -> None:
        return None


class VeeamRestorePoint(BaseModel):
    id: str
    name: str = ""
    creationTime: datetime
    objectId: str = ""
    backupSize: int = 0

    # Legacy aliases used by existing activities
    @property
    def creation_time(self) -> datetime:
        return self.creationTime

    @property
    def is_consistent(self) -> bool:
        return True


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
