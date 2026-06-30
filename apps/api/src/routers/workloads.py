from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AdminUser, AuthUser
from src.db.session import get_db
from src.models.workload import Workload

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
    user: AuthUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list:
    from src.models.appliance import Appliance
    offset = (page - 1) * page_size
    rows = await db.execute(
        select(Workload)
        .join(Appliance, Workload.appliance_id == Appliance.id)
        .where(Appliance.org_id == user.org_id)
        .offset(offset)
        .limit(page_size)
    )
    return rows.scalars().all()


@router.get("/{workload_id}", response_model=WorkloadResponse)
async def get_workload(
    workload_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> Workload:
    from src.models.appliance import Appliance
    row = await db.scalar(
        select(Workload)
        .join(Appliance)
        .where(Workload.id == workload_id, Appliance.org_id == user.org_id)
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Workload not found")
    return row


@router.put("/{workload_id}/targets")
async def set_targets(
    workload_id: uuid.UUID,
    req: SetTargetsRequest,
    user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import update

    # Verify ownership then update
    await get_workload(workload_id, user, db)
    await db.execute(
        update(Workload)
        .where(Workload.id == workload_id)
        .values(rto_target_mins=req.rto_target_mins, rpo_target_mins=req.rpo_target_mins)
    )
    await db.commit()
    return {"status": "updated"}


class SetScheduleRequest(BaseModel):
    schedule_cron: str | None  # e.g. "0 2 * * *" for daily at 2 AM, None to disable


@router.put("/{workload_id}/schedule")
async def set_schedule(
    workload_id: uuid.UUID,
    req: SetScheduleRequest,
    user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import update
    await get_workload(workload_id, user, db)
    await db.execute(
        update(Workload)
        .where(Workload.id == workload_id)
        .values(schedule_cron=req.schedule_cron)
    )
    await db.commit()
    return {"status": "updated", "schedule_cron": req.schedule_cron}


@router.get("/{workload_id}/history")
async def get_history(
    workload_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> list:
    from src.models.test_run import TestRun
    # Verify ownership
    await get_workload(workload_id, user, db)
    rows = await db.execute(
        select(TestRun)
        .where(TestRun.workload_id == workload_id)
        .order_by(TestRun.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "rto_actual_mins": r.rto_actual_mins,
            "rpo_actual_mins": r.rpo_actual_mins,
            "readiness_score": r.readiness_score,
        }
        for r in rows.scalars().all()
    ]
