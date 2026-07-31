# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.appliance import Appliance
from src.models.test_run import TestRun
from src.models.workload import Workload
from src.services.readiness_scoring import (
    bucket_weekly_pass_rate,
    compute_composite_score,
)

router = APIRouter()


@router.get("/readiness")
async def org_readiness(
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Distinct workload counts (avoid inflating by the number of test runs).
    total = await db.scalar(
        select(func.count(func.distinct(Workload.id)))
        .select_from(Workload).join(Appliance)
        .where(Appliance.org_id == user.org_id)
    ) or 0
    tested = await db.scalar(
        select(func.count(func.distinct(TestRun.workload_id)))
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == user.org_id, TestRun.status.in_(["passed", "failed"]))
    ) or 0
    passing = await db.scalar(
        select(func.count(func.distinct(TestRun.workload_id)))
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == user.org_id, TestRun.status == "passed")
    ) or 0

    # Run-level RTO/RPO compliance among passed runs.
    rrow = (await db.execute(
        select(
            func.count(TestRun.id).filter(TestRun.status == "passed").label("passed"),
            func.count(TestRun.id).filter(
                TestRun.status == "passed",
                TestRun.rto_actual_mins <= Workload.rto_target_mins,
            ).label("rto_ok"),
            func.count(TestRun.id).filter(
                TestRun.status == "passed",
                TestRun.rpo_actual_mins <= Workload.rpo_target_mins,
            ).label("rpo_ok"),
        )
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == user.org_id)
    )).one()
    total_passed = rrow.passed or 0
    rto_pct = int(rrow.rto_ok / total_passed * 100) if total_passed else 0
    rpo_pct = int(rrow.rpo_ok / total_passed * 100) if total_passed else 0

    # Rolling 12-week pass-rate trend.
    since = datetime.now(UTC) - timedelta(weeks=12)
    trend_rows = (await db.execute(
        select(TestRun.completed_at, TestRun.status)
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(
            Appliance.org_id == user.org_id,
            TestRun.completed_at.isnot(None),
            TestRun.completed_at >= since,
        )
    )).all()
    runs = [(ts, status == "passed") for ts, status in trend_rows]
    trend = bucket_weekly_pass_rate(runs, weeks=12)

    return {
        "overall_score": compute_composite_score(total, tested, passing, rto_pct),
        "workloads_tested": tested,
        "workloads_total": total,
        "workloads_passing": passing,
        "rto_compliance_pct": rto_pct,
        "rpo_compliance_pct": rpo_pct,
        "trend": trend,
    }


@router.get("/coverage")
async def coverage(
    user: AuthUser,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from datetime import datetime, timedelta

    since = datetime.now(UTC) - timedelta(days=days)

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
