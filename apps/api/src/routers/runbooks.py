"""DR Runbook CRUD, execution trigger, and live status."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.runbook import Runbook, RunbookStep, RunbookExecution, RunbookExecutionStep
from src.services.runbook_engine import build_execution_plan, resolve_execution_order
from src.services.rbac import require_permission

router = APIRouter()

VALID_SCENARIOS = {"ransomware", "datacenter_failure", "cloud_outage", "site_failover", "custom"}
VALID_STEP_TYPES = {"recover_workload", "health_check", "notify", "wait", "manual_gate", "run_script"}


class RunbookStepRequest(BaseModel):
    seq: int
    name: str
    step_type: str
    workload_id: uuid.UUID | None = None
    depends_on_seq: list[int] = []
    parallel: bool = False
    timeout_mins: int = 60
    config: dict = {}
    on_failure: str = "stop"


class CreateRunbookRequest(BaseModel):
    name: str
    description: str = ""
    scenario: str
    rto_target_mins: int | None = None
    tags: list[str] = []
    steps: list[RunbookStepRequest] = []


@router.get("")
async def list_runbooks(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    rows = await db.execute(
        select(Runbook)
        .where(Runbook.org_id == user.org_id, Runbook.enabled == True)
        .order_by(Runbook.created_at.desc())
    )
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "scenario": r.scenario,
            "rto_target_mins": r.rto_target_mins,
            "tags": r.tags,
            "last_executed_at": r.last_executed_at.isoformat() if r.last_executed_at else None,
            "last_execution_status": r.last_execution_status,
        }
        for r in rows.scalars().all()
    ]


@router.post("", status_code=201)
async def create_runbook(body: CreateRunbookRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:write")
    if body.scenario not in VALID_SCENARIOS:
        raise HTTPException(400, f"scenario must be one of: {', '.join(sorted(VALID_SCENARIOS))}")
    for step in body.steps:
        if step.step_type not in VALID_STEP_TYPES:
            raise HTTPException(400, f"step_type must be one of: {', '.join(sorted(VALID_STEP_TYPES))}")
        if step.on_failure not in {"stop", "continue", "rollback"}:
            raise HTTPException(400, "on_failure must be stop, continue, or rollback")

    if body.steps:
        try:
            resolve_execution_order([s.model_dump() for s in body.steps])
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    runbook = Runbook(
        org_id=user.org_id,
        name=body.name,
        description=body.description,
        scenario=body.scenario,
        rto_target_mins=body.rto_target_mins,
        tags=body.tags,
        created_by=getattr(user, "user_id", None),
    )
    db.add(runbook)
    await db.flush()

    for step_req in body.steps:
        step = RunbookStep(
            runbook_id=runbook.id,
            seq=step_req.seq,
            name=step_req.name,
            step_type=step_req.step_type,
            workload_id=step_req.workload_id,
            depends_on_seq=step_req.depends_on_seq,
            parallel=step_req.parallel,
            timeout_mins=step_req.timeout_mins,
            config=step_req.config,
            on_failure=step_req.on_failure,
        )
        db.add(step)

    await db.commit()
    await db.refresh(runbook)
    return {"id": str(runbook.id), "name": runbook.name, "scenario": runbook.scenario}


@router.get("/{runbook_id}")
async def get_runbook(runbook_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    runbook = await db.scalar(
        select(Runbook).where(Runbook.id == runbook_id, Runbook.org_id == user.org_id)
    )
    if not runbook:
        raise HTTPException(404, "Runbook not found")

    steps_rows = await db.execute(
        select(RunbookStep).where(RunbookStep.runbook_id == runbook_id).order_by(RunbookStep.seq)
    )
    steps = steps_rows.scalars().all()

    plan = None
    if steps:
        plan = build_execution_plan(
            {"id": runbook.id, "name": runbook.name, "scenario": runbook.scenario, "rto_target_mins": runbook.rto_target_mins},
            [{"seq": s.seq, "name": s.name, "step_type": s.step_type, "depends_on_seq": s.depends_on_seq, "parallel": s.parallel, "timeout_mins": s.timeout_mins, "on_failure": s.on_failure, "config": s.config} for s in steps],
        )

    return {
        "id": str(runbook.id),
        "name": runbook.name,
        "description": runbook.description,
        "scenario": runbook.scenario,
        "rto_target_mins": runbook.rto_target_mins,
        "tags": runbook.tags,
        "steps": [
            {
                "id": str(s.id),
                "seq": s.seq,
                "name": s.name,
                "step_type": s.step_type,
                "workload_id": str(s.workload_id) if s.workload_id else None,
                "depends_on_seq": s.depends_on_seq,
                "parallel": s.parallel,
                "timeout_mins": s.timeout_mins,
                "on_failure": s.on_failure,
                "config": s.config,
            }
            for s in steps
        ],
        "execution_plan": plan,
    }


@router.post("/{runbook_id}/execute", status_code=201)
async def trigger_execution(
    runbook_id: uuid.UUID,
    body: dict,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "test_runs:trigger")
    runbook = await db.scalar(
        select(Runbook).where(Runbook.id == runbook_id, Runbook.org_id == user.org_id)
    )
    if not runbook:
        raise HTTPException(404, "Runbook not found")

    steps_rows = await db.execute(
        select(RunbookStep).where(RunbookStep.runbook_id == runbook_id).order_by(RunbookStep.seq)
    )
    steps = steps_rows.scalars().all()
    if not steps:
        raise HTTPException(400, "Runbook has no steps configured")

    execution = RunbookExecution(
        runbook_id=runbook_id,
        org_id=user.org_id,
        triggered_by=getattr(user, "user_id", None),
        trigger_reason=body.get("reason", "manual"),
        status="pending",
        target_rto_mins=runbook.rto_target_mins,
    )
    db.add(execution)
    await db.flush()

    for step in steps:
        exec_step = RunbookExecutionStep(
            execution_id=execution.id,
            step_id=step.id,
            seq=step.seq,
            name=step.name,
            step_type=step.step_type,
            status="pending",
        )
        db.add(exec_step)

    runbook.last_executed_at = datetime.now(timezone.utc)
    runbook.last_execution_status = "running"
    await db.commit()
    await db.refresh(execution)

    return {
        "execution_id": str(execution.id),
        "runbook_id": str(runbook_id),
        "status": execution.status,
        "step_count": len(steps),
    }


@router.get("/{runbook_id}/executions")
async def list_executions(runbook_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "test_runs:read")
    rows = await db.execute(
        select(RunbookExecution)
        .where(RunbookExecution.runbook_id == runbook_id, RunbookExecution.org_id == user.org_id)
        .order_by(RunbookExecution.created_at.desc())
        .limit(20)
    )
    return [
        {
            "id": str(e.id),
            "status": e.status,
            "trigger_reason": e.trigger_reason,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "actual_rto_mins": e.actual_rto_mins,
            "target_rto_mins": e.target_rto_mins,
            "rto_met": e.rto_met,
        }
        for e in rows.scalars().all()
    ]


@router.get("/executions/{execution_id}/steps")
async def get_execution_steps(execution_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "test_runs:read")
    rows = await db.execute(
        select(RunbookExecutionStep)
        .where(RunbookExecutionStep.execution_id == execution_id)
        .order_by(RunbookExecutionStep.seq)
    )
    return [
        {
            "id": str(s.id),
            "seq": s.seq,
            "name": s.name,
            "step_type": s.step_type,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "duration_secs": s.duration_secs,
            "output": s.output,
            "error": s.error,
        }
        for s in rows.scalars().all()
    ]
