from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class VeeamJob(BaseModel):
    id: str
    name: str
    type: str
    is_enabled: bool = Field(alias="isEnabled", default=True)
    last_run: datetime | None = Field(alias="lastRun", default=None)
    status: str | None = None

    model_config = {"populate_by_name": True}


class VeeamVM(BaseModel):
    object_id: str = Field(alias="objectId")
    name: str
    platform: str
    job_id: str = Field(alias="jobId")
    last_backup: datetime | None = Field(alias="lastBackup", default=None)
    restore_points_count: int = Field(alias="restorePointsCount", default=0)

    model_config = {"populate_by_name": True}


class VeeamRestorePoint(BaseModel):
    id: str
    creation_time: datetime = Field(alias="creationTime")
    object_id: str = Field(alias="objectId")
    is_consistent: bool = Field(alias="isConsistent", default=True)
    backup_size_bytes: int = Field(alias="backupSizeBytes", default=0)

    model_config = {"populate_by_name": True}
