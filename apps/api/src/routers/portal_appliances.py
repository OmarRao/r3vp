"""Portal-facing appliances endpoints (authenticated via Auth0 JWT, not mTLS)."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.appliance import Appliance
from src.models.workload import Workload

router = APIRouter()


class ApplianceResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str | None
    status: str
    last_heartbeat: str | None
    mtls_thumbprint: str
    workload_count: int = 0
    created_at: str
    model_config = {"from_attributes": False}


@router.get("", response_model=list[ApplianceResponse])
async def list_portal_appliances(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> list:
    rows = await db.execute(
        select(Appliance).where(Appliance.org_id == user.org_id).order_by(Appliance.created_at.desc())
    )
    appliances = rows.scalars().all()
    result = []
    for a in appliances:
        count = await db.scalar(
            select(func.count(Workload.id)).where(Workload.appliance_id == a.id)
        ) or 0
        result.append(ApplianceResponse(
            id=a.id,
            name=a.name,
            version=a.version,
            status=a.status,
            last_heartbeat=a.last_heartbeat.isoformat() if a.last_heartbeat else None,
            mtls_thumbprint=a.mtls_thumbprint,
            workload_count=count,
            created_at=a.created_at.isoformat(),
        ))
    return result


@router.get("/{appliance_id}", response_model=ApplianceResponse)
async def get_portal_appliance(
    appliance_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> ApplianceResponse:
    a = await db.scalar(
        select(Appliance).where(Appliance.id == appliance_id, Appliance.org_id == user.org_id)
    )
    if not a:
        raise HTTPException(404, "Appliance not found")
    count = await db.scalar(
        select(func.count(Workload.id)).where(Workload.appliance_id == a.id)
    ) or 0
    return ApplianceResponse(
        id=a.id, name=a.name, version=a.version, status=a.status,
        last_heartbeat=a.last_heartbeat.isoformat() if a.last_heartbeat else None,
        mtls_thumbprint=a.mtls_thumbprint, workload_count=count,
        created_at=a.created_at.isoformat(),
    )


@router.delete("/{appliance_id}", status_code=204)
async def deregister_appliance(
    appliance_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    from sqlalchemy import update
    a = await db.scalar(
        select(Appliance).where(Appliance.id == appliance_id, Appliance.org_id == user.org_id)
    )
    if not a:
        raise HTTPException(404, "Appliance not found")
    await db.execute(
        update(Appliance).where(Appliance.id == appliance_id).values(status="deregistered")
    )
    await db.commit()
