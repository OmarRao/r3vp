# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Executive reporting: CISO scorecard, trend data, digest schedule."""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser, resolve_local_user_id
from src.db.session import get_db
from src.models.executive_report import DigestSchedule, ScorecardSnapshot
from src.services.executive_report import render_scorecard_pdf
from src.services.executive_snapshot import build_live_scorecard
from src.services.rbac import require_permission

router = APIRouter()


class DigestScheduleRequest(BaseModel):
    cadence: str  # weekly | monthly | quarterly
    recipients: list[str]
    include_scorecard: bool = True
    include_trend_chart: bool = True
    include_provider_breakdown: bool = True
    include_top_risks: bool = True


@router.get("/scorecard")
async def get_scorecard(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "reports:read")
    snapshot = await db.scalar(
        select(ScorecardSnapshot)
        .where(ScorecardSnapshot.org_id == user.org_id)
        .order_by(ScorecardSnapshot.created_at.desc())
    )
    if snapshot:
        return {
            "overall_score": snapshot.overall_score,
            "workloads_total": snapshot.workloads_total,
            "workloads_tested": snapshot.workloads_tested,
            "workloads_passing": snapshot.workloads_passing,
            "rto_compliance_pct": snapshot.rto_compliance_pct,
            "active_threats": snapshot.active_threats,
            "open_incidents": snapshot.open_incidents,
            "provider_breakdown": snapshot.provider_breakdown,
            "top_risks": snapshot.top_risks,
            "snapshot_date": snapshot.snapshot_date,
        }
    # No persisted snapshot yet: compute live from current workloads/tests.
    live, _trend, _org = await build_live_scorecard(db, user.org_id)
    return live


@router.get("/trend")
async def get_trend(
    user: AuthUser,
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "reports:read")
    rows = await db.execute(
        select(ScorecardSnapshot)
        .where(ScorecardSnapshot.org_id == user.org_id)
        .order_by(ScorecardSnapshot.created_at.desc())
        .limit(months)
    )
    snapshots = rows.scalars().all()
    if snapshots:
        return [
            {
                "date": s.snapshot_date,
                "score": s.overall_score,
                "passing": s.workloads_passing,
                "total": s.workloads_total,
                "rto_pct": s.rto_compliance_pct,
            }
            for s in reversed(snapshots)
        ]
    # No persisted history: derive the trend from live weekly pass rates.
    _snap, trend, _org = await build_live_scorecard(db, user.org_id)
    return trend[-months:]


@router.post("/scorecard/pdf")
async def download_scorecard_pdf(
    user: AuthUser,
    period: str = Query("current", description="current | YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "reports:generate")
    period_label = period if period != "current" else datetime.now(UTC).strftime("%B %Y")
    snapshot, trend, org_name = await build_live_scorecard(db, user.org_id)
    # WeasyPrint rendering is CPU-bound and blocks the event loop; run it in a
    # worker thread so other requests are not stalled during PDF generation.
    pdf_bytes = await asyncio.to_thread(
        render_scorecard_pdf,
        org_name=org_name,
        period_label=period_label,
        snapshot=snapshot,
        trend=trend,
    )
    sha256 = __import__("hashlib").sha256(pdf_bytes).hexdigest()
    filename = f"r3vp-scorecard-{period_label.replace(' ', '-').lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-SHA256": sha256,
        },
    )


@router.get("/digest-schedules")
async def list_digest_schedules(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "reports:read")
    rows = await db.execute(
        select(DigestSchedule)
        .where(DigestSchedule.org_id == user.org_id)
        .order_by(DigestSchedule.created_at.desc())
    )
    schedules = rows.scalars().all()
    return [
        {
            "id": str(s.id),
            "cadence": s.cadence,
            "recipients": s.recipients,
            "enabled": s.enabled,
            "last_sent_at": s.last_sent_at.isoformat() if s.last_sent_at else None,
        }
        for s in schedules
    ]


@router.post("/digest-schedules", status_code=201)
async def create_digest_schedule(
    body: DigestScheduleRequest,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "reports:schedule")
    if body.cadence not in {"weekly", "monthly", "quarterly"}:
        raise HTTPException(400, "cadence must be weekly, monthly, or quarterly")
    schedule = DigestSchedule(
        org_id=user.org_id,
        cadence=body.cadence,
        recipients=body.recipients,
        include_scorecard=body.include_scorecard,
        include_trend_chart=body.include_trend_chart,
        include_provider_breakdown=body.include_provider_breakdown,
        include_top_risks=body.include_top_risks,
        created_by=await resolve_local_user_id(db, user),
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return {"id": str(schedule.id), "cadence": schedule.cadence, "recipients": schedule.recipients}


@router.delete("/digest-schedules/{schedule_id}", status_code=204)
async def delete_digest_schedule(
    schedule_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "reports:schedule")
    schedule = await db.scalar(
        select(DigestSchedule).where(
            DigestSchedule.id == schedule_id,
            DigestSchedule.org_id == user.org_id,
        )
    )
    if not schedule:
        raise HTTPException(404, "Digest schedule not found")
    await db.delete(schedule)
    await db.commit()
