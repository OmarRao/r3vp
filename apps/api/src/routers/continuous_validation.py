"""Continuous validation API: policies, micro-validation runs, alerts, live health."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.continuous_validation import (
    ContinuousValidationPolicy,
    MicroValidationRun,
    ValidationAlert,
)
from src.services.continuous_validation import MICRO_CHECKS, compute_continuous_health
from src.services.rbac import require_permission

router = APIRouter()

MOCK_POLICIES = [
    {"id": "p1", "name": "Production Workloads", "enabled": True, "check_interval_mins": 15, "workload_scope": "all", "checks_enabled": {"restore_point_freshness": True, "mount_check": True, "veeam_job_status": True, "agent_heartbeat": True}, "alert_on_failure": True, "consecutive_failures_before_alert": 2},
    {"id": "p2", "name": "Critical Tier Only", "enabled": True, "check_interval_mins": 5, "workload_scope": "tag:critical", "checks_enabled": {"restore_point_freshness": True, "mount_check": True, "veeam_job_status": True, "vcenter_connectivity": True, "rpo_compliance": True}, "alert_on_failure": True, "consecutive_failures_before_alert": 1},
]

MOCK_RECENT_RUNS = [
    {"id": "r1", "workload_name": "db-prod-01", "status": "pass", "checks_run": 4, "checks_passed": 4, "restore_point_age_hours": 1, "ran_at": "2026-06-26T14:00:00Z", "duration_ms": 312},
    {"id": "r2", "workload_name": "dc-prod-02", "status": "pass", "checks_run": 4, "checks_passed": 4, "restore_point_age_hours": 2, "ran_at": "2026-06-26T14:00:00Z", "duration_ms": 289},
    {"id": "r3", "workload_name": "erp-prod-01", "status": "warn", "checks_run": 4, "checks_passed": 3, "restore_point_age_hours": 6, "ran_at": "2026-06-26T14:00:00Z", "duration_ms": 445, "check_results": {"restore_point_freshness": {"status": "warn", "detail": "Latest RP is 6 hours old, RPO target is 4 hours"}}},
    {"id": "r4", "workload_name": "files-prod-01", "status": "fail", "checks_run": 4, "checks_passed": 2, "restore_point_age_hours": 18, "ran_at": "2026-06-26T14:00:00Z", "duration_ms": 580, "check_results": {"restore_point_freshness": {"status": "fail", "detail": "Latest RP is 18 hours old"}, "veeam_job_status": {"status": "fail", "detail": "Last job failed with error E0x8019"}}},
]

MOCK_ALERTS = [
    {"id": "a1", "workload_name": "files-prod-01", "alert_type": "consecutive_failures", "severity": "high", "detail": "3 consecutive micro-validation failures. Last Veeam job failed with E0x8019.", "resolved": False, "created_at": "2026-06-26T13:45:00Z"},
    {"id": "a2", "workload_name": "erp-prod-01", "alert_type": "restore_point_stale", "severity": "medium", "detail": "Restore point age 6h exceeds RPO target of 4h.", "resolved": False, "created_at": "2026-06-26T14:00:00Z"},
]


class CreatePolicyRequest(BaseModel):
    name: str
    check_interval_mins: int = 15
    workload_scope: str = "all"
    workload_ids: list[str] = []
    checks_enabled: dict = {}
    alert_on_failure: bool = True
    consecutive_failures_before_alert: int = 2


@router.get("/checks")
async def list_available_checks():
    return [{"id": k, **v} for k, v in MICRO_CHECKS.items()]


@router.get("/policies")
async def list_policies(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    rows = await db.execute(
        select(ContinuousValidationPolicy)
        .where(ContinuousValidationPolicy.org_id == user.org_id)
        .order_by(ContinuousValidationPolicy.created_at.desc())
    )
    policies = rows.scalars().all()
    if policies:
        return [
            {"id": str(p.id), "name": p.name, "enabled": p.enabled, "check_interval_mins": p.check_interval_mins, "workload_scope": p.workload_scope, "checks_enabled": p.checks_enabled}
            for p in policies
        ]
    return MOCK_POLICIES


@router.post("/policies", status_code=201)
async def create_policy(body: CreatePolicyRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:write")
    if body.check_interval_mins < 1:
        raise HTTPException(400, "check_interval_mins must be >= 1")
    policy = ContinuousValidationPolicy(
        org_id=user.org_id,
        name=body.name,
        check_interval_mins=body.check_interval_mins,
        workload_scope=body.workload_scope,
        workload_ids=body.workload_ids,
        checks_enabled=body.checks_enabled or {k: True for k in MICRO_CHECKS},
        alert_on_failure=body.alert_on_failure,
        consecutive_failures_before_alert=body.consecutive_failures_before_alert,
        created_by=getattr(user, "user_id", None),
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return {"id": str(policy.id), "name": policy.name}


@router.patch("/policies/{policy_id}/toggle")
async def toggle_policy(policy_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:write")
    policy = await db.scalar(
        select(ContinuousValidationPolicy)
        .where(ContinuousValidationPolicy.id == policy_id, ContinuousValidationPolicy.org_id == user.org_id)
    )
    if not policy:
        raise HTTPException(404, "Policy not found")
    policy.enabled = not policy.enabled
    await db.commit()
    return {"id": str(policy.id), "enabled": policy.enabled}


@router.get("/runs")
async def recent_runs(user: AuthUser, limit: int = 50, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    rows = await db.execute(
        select(MicroValidationRun)
        .where(MicroValidationRun.org_id == user.org_id)
        .order_by(MicroValidationRun.ran_at.desc())
        .limit(limit)
    )
    runs = rows.scalars().all()
    if runs:
        return [
            {"id": str(r.id), "workload_name": r.workload_name, "status": r.status, "checks_run": r.checks_run, "checks_passed": r.checks_passed, "restore_point_age_hours": r.restore_point_age_hours, "ran_at": r.ran_at.isoformat(), "duration_ms": r.duration_ms}
            for r in runs
        ]
    return MOCK_RECENT_RUNS


@router.get("/health")
async def continuous_health(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    rows = await db.execute(
        select(MicroValidationRun)
        .where(MicroValidationRun.org_id == user.org_id)
        .order_by(MicroValidationRun.ran_at.desc())
        .limit(100)
    )
    runs = [{"status": r.status, "ran_at": r.ran_at.isoformat()} for r in rows.scalars().all()]
    if not runs:
        runs = [{"status": r["status"], "ran_at": r["ran_at"]} for r in MOCK_RECENT_RUNS]
    return compute_continuous_health(runs)


@router.get("/alerts")
async def list_alerts(user: AuthUser, resolved: bool = False, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    rows = await db.execute(
        select(ValidationAlert)
        .where(ValidationAlert.org_id == user.org_id, ValidationAlert.resolved == resolved)
        .order_by(ValidationAlert.created_at.desc())
        .limit(50)
    )
    alerts = rows.scalars().all()
    if alerts:
        return [
            {"id": str(a.id), "workload_name": a.workload_name, "alert_type": a.alert_type, "severity": a.severity, "detail": a.detail, "resolved": a.resolved, "created_at": a.created_at.isoformat()}
            for a in alerts
        ]
    return [a for a in MOCK_ALERTS if a["resolved"] == resolved]


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:write")
    alert = await db.scalar(
        select(ValidationAlert)
        .where(ValidationAlert.id == alert_id, ValidationAlert.org_id == user.org_id)
    )
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.resolved = True
    alert.resolved_at = datetime.now(UTC)
    await db.commit()
    return {"id": str(alert.id), "resolved": True}
