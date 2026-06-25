"""Appliance fleet management: groups, health, bulk config, cross-site view."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.fleet import ApplianceGroup, ApplianceGroupMember, ApplianceHealthSnapshot, BulkConfigJob
from src.services.rbac import require_permission

router = APIRouter()

MOCK_FLEET = [
    {"id": "a1", "name": "NYC-Primary", "site": "NYC DC1", "status": "healthy", "workloads": 20, "cpu": 24, "memory": 41, "disk": 38, "veeam": True, "vcenter": True, "temporal": True, "version": "0.13.0", "uptime_hours": 720, "last_test": "Today 14:22"},
    {"id": "a2", "name": "NYC-DR", "site": "NYC DR Site", "status": "healthy", "workloads": 8, "cpu": 12, "memory": 28, "disk": 22, "veeam": True, "vcenter": True, "temporal": True, "version": "0.13.0", "uptime_hours": 168, "last_test": "Jun 20"},
    {"id": "a3", "name": "Azure-EastUS", "site": "Azure East US", "status": "warning", "workloads": 10, "cpu": 18, "memory": 65, "disk": 71, "veeam": True, "vcenter": False, "temporal": True, "version": "0.12.1", "uptime_hours": 504, "last_test": "Jun 18", "alerts": ["Disk usage above 70%", "vCenter connection lost"]},
    {"id": "a4", "name": "AWS-USEast1", "site": "AWS us-east-1", "status": "healthy", "workloads": 8, "cpu": 9, "memory": 33, "disk": 28, "veeam": True, "vcenter": False, "temporal": True, "version": "0.13.0", "uptime_hours": 336, "last_test": "Jun 21"},
    {"id": "a5", "name": "London-DC", "site": "London DC", "status": "offline", "workloads": 0, "cpu": None, "memory": None, "disk": None, "veeam": False, "vcenter": False, "temporal": False, "version": "0.11.2", "uptime_hours": None, "last_test": "Jun 10", "alerts": ["No heartbeat in 72 hours"]},
]


class CreateGroupRequest(BaseModel):
    name: str
    description: str = ""
    site_name: str | None = None
    region: str | None = None
    tags: list[str] = []
    config_template: dict = {}


class BulkConfigRequest(BaseModel):
    appliance_ids: list[str]
    config: dict


@router.get("/overview")
async def fleet_overview(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "appliances:read")
    healthy = sum(1 for a in MOCK_FLEET if a["status"] == "healthy")
    warning = sum(1 for a in MOCK_FLEET if a["status"] == "warning")
    offline = sum(1 for a in MOCK_FLEET if a["status"] == "offline")
    total_workloads = sum(a["workloads"] for a in MOCK_FLEET)
    return {
        "total_appliances": len(MOCK_FLEET),
        "healthy": healthy,
        "warning": warning,
        "offline": offline,
        "total_workloads": total_workloads,
        "appliances": MOCK_FLEET,
    }


@router.get("/health")
async def get_fleet_health(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "appliances:read")
    rows = await db.execute(
        select(ApplianceHealthSnapshot)
        .where(ApplianceHealthSnapshot.org_id == user.org_id)
        .order_by(ApplianceHealthSnapshot.recorded_at.desc())
        .limit(50)
    )
    snapshots = rows.scalars().all()
    if snapshots:
        return [
            {
                "appliance_id": str(s.appliance_id),
                "status": s.status,
                "cpu_pct": s.cpu_pct,
                "memory_pct": s.memory_pct,
                "disk_pct": s.disk_pct,
                "veeam_connected": s.veeam_connected,
                "workload_count": s.workload_count,
                "version": s.version,
                "alerts": s.alerts,
                "recorded_at": s.recorded_at.isoformat(),
            }
            for s in snapshots
        ]
    return MOCK_FLEET


@router.get("/groups")
async def list_groups(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "appliances:read")
    rows = await db.execute(
        select(ApplianceGroup)
        .where(ApplianceGroup.org_id == user.org_id)
        .order_by(ApplianceGroup.created_at.desc())
    )
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "site_name": g.site_name,
            "region": g.region,
            "tags": g.tags,
        }
        for g in rows.scalars().all()
    ]


@router.post("/groups", status_code=201)
async def create_group(body: CreateGroupRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "appliances:manage")
    group = ApplianceGroup(
        org_id=user.org_id,
        name=body.name,
        description=body.description,
        site_name=body.site_name,
        region=body.region,
        tags=body.tags,
        config_template=body.config_template,
        created_by=getattr(user, "user_id", None),
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return {"id": str(group.id), "name": group.name}


@router.post("/bulk-config", status_code=201)
async def push_bulk_config(body: BulkConfigRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "appliances:manage")
    if not body.appliance_ids:
        raise HTTPException(400, "appliance_ids must not be empty")
    job = BulkConfigJob(
        org_id=user.org_id,
        config=body.config,
        target_appliance_ids=body.appliance_ids,
        status="pending",
        created_by=getattr(user, "user_id", None),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return {"job_id": str(job.id), "status": "pending", "target_count": len(body.appliance_ids)}


@router.get("/bulk-config/{job_id}")
async def get_bulk_config_status(job_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "appliances:read")
    job = await db.scalar(
        select(BulkConfigJob).where(BulkConfigJob.id == job_id, BulkConfigJob.org_id == user.org_id)
    )
    if not job:
        raise HTTPException(404, "Config job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "results": job.results,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
