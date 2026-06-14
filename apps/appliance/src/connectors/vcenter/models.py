from __future__ import annotations
from pydantic import BaseModel


class VCenterVM(BaseModel):
    moref: str
    name: str
    power_state: str
    guest_os: str
    ip_address: str | None = None
    tools_status: str | None = None
    num_cpu: int = 0
    memory_mb: int = 0


class VCenterNetwork(BaseModel):
    moref: str
    name: str


class VCenterDatastore(BaseModel):
    moref: str
    name: str
    free_bytes: int = 0
    capacity_bytes: int = 0
