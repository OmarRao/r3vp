"""Executive reporting: CISO scorecard, trend data, digest schedule."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.executive_report import DigestSchedule, ScorecardSnapshot
from src.services.executive_report import compute_scorecard, render_scorecard_pdf
from src.services.rbac import require_permission

router = APIRouter()


class DigestScheduleRequest(BaseModel):
    cadence: str  # weekly | monthly | quarterly
    recipients: list[str]
    include_scorecard: bool = True
    include_trend_chart: bool = True
    include_provider_breakdown: bool = True
    include_top_risks: bool = True


MOCK_SNAPSHOT = {
    "overall_score": 84,
    "workloads_total": 47,
    "workloads_tested": 44,
    "workloads_passing": 41,
    "rto_compliance_pct": 87,
    "active_threats": 1,
    "open_incidents": 0,
    "provider_breakdown": {
        "vmware": {"total": 20, "tested": 20, "pass_rate": 95},
        "azure": {"total": 10, "tested": 10, "pass_rate": 80},
        "aws": {"total": 8, "tested": 8, "pass_rate": 75},
        "gcp": {"total": 5, "tested": 4, "pass_rate": 75},
        "hyperv": {"total": 4, "tested": 2, "pass_rate": 100},
    },
    "top_risks": [
        {"workload": "db-prod-03", "severity": "high", "reason": "RTO exceeded target by 42 minutes in last 2 tests"},
        {"workload": "auth-svc-01", "severity": "medium", "reason": "Not tested in 45 days"},
        {"workload": "erp-prod-01", "severity": "medium", "reason": "Pass rate dropped from 100% to 67% this quarter"},
    ],
}

MOCK_TREND = [
    {"date": "Jan 2026", "score": 71, "passing": 34, "total": 47, "rto_pct": 72},
    {"date": "Feb 2026", "score": 74, "passing": 36, "total": 47, "rto_pct": 76},
    {"date": "Mar 2026", "score": 78, "passing": 38, "total": 47, "rto_pct": 80},
    {"date": "Apr 2026", "score": 80, "passing": 39, "total": 47, "rto_pct": 83},
    {"date": "May 2026", "score": 82, "passing": 40, "total": 47, "rto_pct": 85},
    {"date": "Jun 2026", "score": 84, "passing": 41, "total": 47, "rto_pct": 87},
]


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
    return MOCK_SNAPSHOT


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
    return MOCK_TREND[-months:]


@router.post("/scorecard/pdf")
async def download_scorecard_pdf(
    user: AuthUser,
    period: str = Query("current", description="current | YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "reports:generate")
    period_label = period if period != "current" else datetime.now(timezone.utc).strftime("%B %Y")
    pdf_bytes = render_scorecard_pdf(
        org_name="Your Organization",
        period_label=period_label,
        snapshot=MOCK_SNAPSHOT,
        trend=MOCK_TREND,
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
        created_by=getattr(user, "user_id", None),
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
