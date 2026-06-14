from __future__ import annotations
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.config import settings
from src.db.session import get_db
from src.models.test_run import TestRun, TestRunStep
from src.models.workload import Workload
from src.models.appliance import Appliance

log = structlog.get_logger()

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

    # Enqueue Temporal workflow if client is available
    try:
        from src.main import get_temporal_client
        tc = get_temporal_client()
        wf_handle = await tc.start_workflow(
            "RecoveryTestWorkflow",
            args=[str(run.id), str(workload.id), str(workload.appliance_id)],
            id=str(run.id),
            task_queue=settings.temporal_task_queue,
        )
        from sqlalchemy import update
        await db.execute(
            update(TestRun).where(TestRun.id == run.id).values(
                workflow_run_id=wf_handle.first_execution_run_id,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        await db.refresh(run)
    except Exception as exc:
        log.warning("temporal enqueue failed, run stays pending", error=str(exc))

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
):
    from fastapi.responses import Response
    from jinja2 import Environment, FileSystemLoader
    import weasyprint
    import os
    from src.models.test_run import HealthCheckResult

    run_data = await get_test_run(run_id, user, db)

    # Load health checks
    hc_rows = await db.execute(
        select(HealthCheckResult).where(HealthCheckResult.run_id == run_id)
    )
    health_checks = [
        {"check_name": h.check_name, "passed": h.passed, "output": h.output}
        for h in hc_rows.scalars().all()
    ]

    # Load workload for targets
    workload = await db.scalar(
        select(Workload).where(Workload.id == run_data["workload_id"])
    )

    steps = run_data.get("steps", [])
    for step in steps:
        sa = step.get("started_at")
        ea = step.get("ended_at")
        if sa and ea:
            try:
                delta = datetime.fromisoformat(ea) - datetime.fromisoformat(sa)
                step["duration"] = f"{int(delta.total_seconds())} sec"
            except Exception:
                step["duration"] = ""
        else:
            step["duration"] = ""
        step["detail_summary"] = str(step.get("detail", "") or "")[:80]

    rto_actual = run_data.get("rto_actual_mins") or 0
    rpo_actual = run_data.get("rpo_actual_mins") or 0
    rto_target = workload.rto_target_mins or 0 if workload else 0
    rpo_target = workload.rpo_target_mins or 0 if workload else 0

    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(os.path.abspath(templates_dir)))
    template = env.get_template("report.html")

    html = template.render(
        org_name=str(user.org_id),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        workload_name=workload.name if workload else "Unknown",
        test_date=run_data.get("started_at") or "",
        passed=run_data.get("status") == "passed",
        rto_target=rto_target,
        rto_actual=rto_actual,
        rto_ok=rto_actual <= rto_target if rto_target else True,
        rpo_target=rpo_target,
        rpo_actual=rpo_actual,
        rpo_ok=rpo_actual <= rpo_target if rpo_target else True,
        readiness_score=run_data.get("readiness_score"),
        steps=steps,
        health_checks=health_checks,
        failure_reason=None,
    )

    pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="r3vp-report-{run_id}.pdf"'},
    )
