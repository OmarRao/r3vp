"""Compliance framework builder API: custom frameworks, control mapping, assessment."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.compliance_framework import (
    ComplianceControl,
    ComplianceFramework,
    FrameworkAssessment,
)
from src.services.compliance_framework import (
    BUILTIN_FRAMEWORKS,
    R3VP_EVIDENCE_TYPES,
    R3VP_METRICS,
    evaluate_framework,
)
from src.services.rbac import require_permission

router = APIRouter()


class CreateFrameworkRequest(BaseModel):
    name: str
    short_code: str
    version: str | None = None
    description: str | None = None


class AddControlRequest(BaseModel):
    control_id: str
    title: str
    description: str | None = None
    category: str | None = None
    r3vp_evidence_types: list[str] = []
    r3vp_metric: str | None = None
    pass_threshold: int | None = None
    weight: int = 1


class RunAssessmentRequest(BaseModel):
    framework_id: uuid.UUID
    period_start: str
    period_end: str
    pass_rate: float = 0.0
    rto_compliance: float = 0.0
    coverage_pct: float = 0.0


@router.get("/catalog")
async def list_builtin_frameworks():
    return [
        {
            "short_code": f["short_code"],
            "name": f["name"],
            "version": f["version"],
            "description": f["description"],
            "control_count": len(f["controls"]),
            "is_builtin": True,
        }
        for f in BUILTIN_FRAMEWORKS
    ]


@router.get("/metrics")
async def list_metrics():
    return [{"id": k, "description": v} for k, v in R3VP_METRICS.items()]


@router.get("/evidence-types")
async def list_evidence_types():
    return R3VP_EVIDENCE_TYPES


@router.get("")
async def list_frameworks(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "reports:read")
    rows = await db.execute(
        select(ComplianceFramework)
        .where(ComplianceFramework.org_id == user.org_id)
        .order_by(ComplianceFramework.created_at.desc())
    )
    custom = rows.scalars().all()
    builtin = [
        {"id": f["short_code"], "name": f["name"], "short_code": f["short_code"], "version": f["version"], "is_builtin": True, "control_count": len(f["controls"]), "enabled": True}
        for f in BUILTIN_FRAMEWORKS
    ]
    custom_out = [
        {"id": str(f.id), "name": f.name, "short_code": f.short_code, "version": f.version, "is_builtin": False, "enabled": f.enabled}
        for f in custom
    ]
    return builtin + custom_out


@router.post("", status_code=201)
async def create_framework(body: CreateFrameworkRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "reports:write")
    framework = ComplianceFramework(
        org_id=user.org_id,
        name=body.name,
        short_code=body.short_code.upper(),
        version=body.version,
        description=body.description,
        is_builtin=False,
        created_by=getattr(user, "user_id", None),
    )
    db.add(framework)
    await db.commit()
    await db.refresh(framework)
    return {"id": str(framework.id), "name": framework.name, "short_code": framework.short_code}


@router.get("/{framework_id}/controls")
async def list_controls(framework_id: str, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "reports:read")
    builtin = next((f for f in BUILTIN_FRAMEWORKS if f["short_code"] == framework_id), None)
    if builtin:
        return builtin["controls"]
    try:
        fid = uuid.UUID(framework_id)
    except ValueError as exc:
        raise HTTPException(404, "Framework not found") from exc
    rows = await db.execute(
        select(ComplianceControl)
        .where(ComplianceControl.framework_id == fid)
        .order_by(ComplianceControl.created_at)
    )
    return [
        {"control_id": c.control_id, "title": c.title, "category": c.category, "r3vp_metric": c.r3vp_metric, "pass_threshold": c.pass_threshold, "weight": c.weight}
        for c in rows.scalars().all()
    ]


@router.post("/{framework_id}/controls", status_code=201)
async def add_control(framework_id: uuid.UUID, body: AddControlRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "reports:write")
    invalid = [e for e in body.r3vp_evidence_types if e not in R3VP_EVIDENCE_TYPES]
    if invalid:
        raise HTTPException(400, f"Unknown evidence types: {invalid}. Valid: {R3VP_EVIDENCE_TYPES}")
    if body.r3vp_metric and body.r3vp_metric not in R3VP_METRICS:
        raise HTTPException(400, f"Unknown metric: {body.r3vp_metric}. Valid: {list(R3VP_METRICS)}")
    control = ComplianceControl(
        framework_id=framework_id,
        control_id=body.control_id,
        title=body.title,
        description=body.description,
        category=body.category,
        r3vp_evidence_types=body.r3vp_evidence_types,
        r3vp_metric=body.r3vp_metric,
        pass_threshold=body.pass_threshold,
        weight=body.weight,
    )
    db.add(control)
    await db.commit()
    await db.refresh(control)
    return {"id": str(control.id), "control_id": control.control_id}


@router.post("/assess")
async def run_assessment(body: RunAssessmentRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "reports:write")
    fid = str(body.framework_id)
    builtin = next((f for f in BUILTIN_FRAMEWORKS if f["short_code"] == fid), None)
    if builtin:
        controls = builtin["controls"]
    else:
        rows = await db.execute(
            select(ComplianceControl).where(ComplianceControl.framework_id == body.framework_id)
        )
        controls = [
            {"control_id": c.control_id, "r3vp_metric": c.r3vp_metric, "pass_threshold": c.pass_threshold, "weight": c.weight}
            for c in rows.scalars().all()
        ]
    if not controls:
        raise HTTPException(400, "Framework has no controls defined")

    result = evaluate_framework(controls, body.pass_rate, body.rto_compliance, body.coverage_pct)

    assessment = FrameworkAssessment(
        framework_id=body.framework_id,
        org_id=user.org_id,
        period_start=body.period_start,
        period_end=body.period_end,
        overall_score=result["overall_score"],
        controls_assessed=result["controls_assessed"],
        controls_passing=result["controls_passing"],
        control_results=result["control_results"],
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return {"assessment_id": str(assessment.id), **result}
