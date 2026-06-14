from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db

router = APIRouter()


class WorkloadResponse(BaseModel):
    id: uuid.UUID
    name: str
    platform: str
    os_type: str | None
    is_protected: bool
    rto_target_mins: int | None
    rpo_target_mins: int | None
    last_backup_at: str | None
    last_test_run_status: str | None = None
    last_test_run_at: str | None = None

    model_config = {"from_attributes": True}


class SetTargetsRequest(BaseModel):
    rto_target_mins: int
    rpo_target_mins: int


@router.get("", response_model=list[WorkloadResponse])
async def list_workloads(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list:
    return []


@router.get("/{workload_id}", response_model=WorkloadResponse)
async def get_workload(workload_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    return {}


@router.put("/{workload_id}/targets")
async def set_targets(
    workload_id: uuid.UUID,
    req: SetTargetsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"status": "updated"}


@router.get("/{workload_id}/history")
async def get_history(workload_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list:
    return []
