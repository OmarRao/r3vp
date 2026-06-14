from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.test_run import AuditEvent

router = APIRouter()


@router.get("")
async def list_audit_events(
    user: AuthUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    offset = (page - 1) * page_size
    total = await db.scalar(
        select(func.count(AuditEvent.id)).where(AuditEvent.org_id == user.org_id)
    )
    rows = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.org_id == user.org_id)
        .order_by(AuditEvent.occurred_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return {
        "total": total or 0,
        "events": [
            {
                "id": r.id,
                "actor_type": r.actor_type,
                "actor_id": str(r.actor_id) if r.actor_id else None,
                "event_type": r.event_type,
                "resource_id": str(r.resource_id) if r.resource_id else None,
                "detail": r.detail,
                "occurred_at": r.occurred_at.isoformat(),
            }
            for r in rows.scalars().all()
        ],
    }
