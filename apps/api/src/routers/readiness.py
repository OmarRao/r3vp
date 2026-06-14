from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.workload import Workload
from src.models.appliance import Appliance
from src.models.test_run import TestRun

router = APIRouter()


@router.get("/readiness")
async def org_readiness(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Aggregate readiness across all workloads in this org
    rows = await db.execute(
        select(
            func.count(Workload.id).label("total"),
            func.count(TestRun.id).filter(TestRun.status.in_(["passed", "failed"])).label("tested"),
            func.avg(TestRun.readiness_score).label("avg_score"),
            func.count(TestRun.id).filter(
                TestRun.status == "passed",
                TestRun.rto_actual_mins <= Workload.rto_target_mins,
            ).label("rto_pass"),
            func.count(TestRun.id).filter(
                TestRun.status == "passed",
                TestRun.rpo_actual_mins <= Workload.rpo_target_mins,
            ).label("rpo_pass"),
            func.count(TestRun.id).filter(TestRun.status == "passed").label("total_passed"),
        )
        .select_from(Workload)
        .join(Appliance)
        .outerjoin(
            TestRun,
            TestRun.workload_id == Workload.id,
        )
        .where(Appliance.org_id == user.org_id)
    )
    row = rows.one()

    total = row.total or 0
    tested = row.tested or 0
    avg_score = int(row.avg_score or 0)
    total_passed = row.total_passed or 0
    rto_pct = int(row.rto_pass / total_passed * 100) if total_passed else 0
    rpo_pct = int(row.rpo_pass / total_passed * 100) if total_passed else 0

    return {
        "overall_score": avg_score,
        "workloads_tested": tested,
        "workloads_total": total,
        "rto_compliance_pct": rto_pct,
        "rpo_compliance_pct": rpo_pct,
        "trend": [],  # Phase 5: populate 90-day trend
    }


@router.get("/coverage")
async def coverage(
    user: AuthUser,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from datetime import datetime, timezone, timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_row = await db.scalar(
        select(func.count(Workload.id))
        .join(Appliance)
        .where(Appliance.org_id == user.org_id)
    )
    total = total_row or 0

    tested_row = await db.scalar(
        select(func.count(func.distinct(TestRun.workload_id)))
        .join(Workload)
        .join(Appliance)
        .where(
            Appliance.org_id == user.org_id,
            TestRun.completed_at >= since,
        )
    )
    tested = tested_row or 0
    pct = int(tested / total * 100) if total else 0

    untested = await db.execute(
        select(Workload.id, Workload.name)
        .join(Appliance)
        .where(
            Appliance.org_id == user.org_id,
            Workload.id.not_in(
                select(TestRun.workload_id).where(TestRun.completed_at >= since)
            ),
        )
        .limit(20)
    )

    return {
        "tested_pct": pct,
        "untested_workloads": [
            {"id": str(r.id), "name": r.name} for r in untested.all()
        ],
    }
