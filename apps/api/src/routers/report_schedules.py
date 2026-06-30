"""CRUD endpoints for scheduled compliance report delivery."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.report_schedule import ReportSchedule

router = APIRouter()

VALID_REPORT_TYPES = {"soc2", "iso27001", "nist_csf", "monthly_summary", "cyber_insurance"}
VALID_CRONS = {
    "daily":     "0 8 * * *",
    "weekly":    "0 8 * * 1",
    "monthly":   "0 8 1 * *",
    "quarterly": "0 8 1 1,4,7,10 *",
}


class CreateScheduleRequest(BaseModel):
    name: str
    report_type: str
    cron: str
    period_days: int = 30
    recipients: list[dict]  # [{"type": "email", "destination": "..."}, ...]


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    name: str
    report_type: str
    cron: str
    period_days: int
    recipients: list
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(user: AuthUser, db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(ReportSchedule)
        .where(ReportSchedule.org_id == user.org_id)
        .order_by(ReportSchedule.created_at.desc())
    )
    return rows.scalars().all()


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    body: CreateScheduleRequest,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    if body.report_type not in VALID_REPORT_TYPES:
        raise HTTPException(400, f"report_type must be one of: {', '.join(sorted(VALID_REPORT_TYPES))}")

    cron = VALID_CRONS.get(body.cron, body.cron)

    schedule = ReportSchedule(
        org_id=user.org_id,
        name=body.name,
        report_type=body.report_type,
        cron=cron,
        period_days=body.period_days,
        recipients=body.recipients,
        next_run_at=datetime.now(UTC) + timedelta(days=1),
        created_by=getattr(user, "user_id", None),
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.patch("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.scalar(
        select(ReportSchedule).where(
            ReportSchedule.id == schedule_id,
            ReportSchedule.org_id == user.org_id,
        )
    )
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    schedule.enabled = not schedule.enabled
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    schedule = await db.scalar(
        select(ReportSchedule).where(
            ReportSchedule.id == schedule_id,
            ReportSchedule.org_id == user.org_id,
        )
    )
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    await db.delete(schedule)
    await db.commit()
