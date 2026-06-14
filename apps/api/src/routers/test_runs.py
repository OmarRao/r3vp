from __future__ import annotations
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.test_run import TestRun, TestRunStep
from src.models.workload import Workload
from src.models.appliance import Appliance

router = APIRouter()


class TriggerTestRunRequest(BaseModel):
    workload_id: uuid.UUID
    restore_point: str | None = None


class TestRunResponse(BaseModel):
    id: uuid.UUID
    workload_id: uuid.UUID
    status: str
    started_at: str | None
    completed_at: str | None
    rto_actual_mins: int | None
    rpo_actual_mins: int | None
    readiness_score: int | None
    steps: list[dict] = []

    model_config = {"from_attributes": True}


async def _owned_workload(
    workload_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession,
) -> Workload:
    row = await db.scalar(
        select(Workload)
        .join(Appliance)
        .where(Workload.id == workload_id, Appliance.org_id == user.org_id)
    )
    if not row:
        raise HTTPException(404, "Workload not found")
    return row


@router.post("", response_model=TestRunResponse)
async def trigger_test_run(
    req: TriggerTestRunRequest,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workload = await _owned_workload(req.workload_id, user, db)

    restore_dt = (
        datetime.fromisoformat(req.restore_point)
        if req.restore_point
        else None
    )

    run = TestRun(
        workload_id=workload.id,
        triggered_by=None,  # TODO: map user.sub -> users.id
        restore_point=restore_dt,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # TODO Phase 3: enqueue Temporal workflow via Temporal Cloud SDK

    return {
        "id": run.id,
        "workload_id": run.workload_id,
        "status": run.status,
        "started_at": None,
        "completed_at": None,
        "rto_actual_mins": None,
        "rpo_actual_mins": None,
        "readiness_score": None,
    }


@router.get("/{run_id}", response_model=TestRunResponse)
async def get_test_run(
    run_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    run = await db.scalar(
        select(TestRun)
        .join(Workload)
        .join(Appliance)
        .where(TestRun.id == run_id, Appliance.org_id == user.org_id)
    )
    if not run:
        raise HTTPException(404, "Test run not found")

    steps = await db.execute(
        select(TestRunStep).where(TestRunStep.run_id == run_id).order_by(TestRunStep.id)
    )
    return {
        "id": run.id,
        "workload_id": run.workload_id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "rto_actual_mins": run.rto_actual_mins,
        "rpo_actual_mins": run.rpo_actual_mins,
        "readiness_score": run.readiness_score,
        "steps": [
            {
                "step_name": s.step_name,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "detail": s.detail,
            }
            for s in steps.scalars().all()
        ],
    }


@router.get("/{run_id}/report")
async def download_report(
    run_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Phase 5: generate presigned S3 URL to PDF report
    await get_test_run(run_id, user, db)
    return {"url": ""}
