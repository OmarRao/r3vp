from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
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


@router.get("/export")
async def export_audit_csv(
    user: AuthUser,
    from_date: str = Query(..., description="ISO date e.g. 2026-01-01"),
    to_date: str = Query(..., description="ISO date e.g. 2026-12-31"),
    db: AsyncSession = Depends(get_db),
):
    import csv
    import io
    from datetime import datetime

    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse

    try:
        from_dt = datetime.fromisoformat(from_date).replace(tzinfo=UTC)
        to_dt = datetime.fromisoformat(to_date).replace(tzinfo=UTC)
    except ValueError as exc:
        raise HTTPException(400, "Invalid date format. Use ISO 8601 e.g. 2026-01-01") from exc

    if (to_dt - from_dt).days > 90:
        raise HTTPException(400, "Date range cannot exceed 90 days")

    rows = await db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.org_id == user.org_id,
            AuditEvent.occurred_at >= from_dt,
            AuditEvent.occurred_at <= to_dt,
        )
        .order_by(AuditEvent.occurred_at.asc())
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["occurred_at", "event_type", "actor_type", "actor_id", "resource_id", "detail"])
    for r in rows.scalars().all():
        writer.writerow([
            r.occurred_at.isoformat(),
            r.event_type,
            r.actor_type,
            str(r.actor_id) if r.actor_id else "",
            str(r.resource_id) if r.resource_id else "",
            str(r.detail or ""),
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="r3vp-audit-{from_date}-{to_date}.csv"'},
    )
