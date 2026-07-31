# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Build a CISO scorecard snapshot from live database state.

Produces the snapshot and trend dicts consumed by the executive endpoints and
`executive_report.render_scorecard_pdf`, computed from real workloads, test
runs, and threats - so the scorecard and board PDF reflect actual data instead
of a static mock.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.appliance import Appliance, Org
from src.models.test_run import TestRun
from src.models.threat_scan import ThreatFinding, ThreatIncident
from src.models.workload import Workload
from src.services.readiness_scoring import (
    bucket_weekly_pass_rate,
    compute_composite_score,
)

RESOLVED_INCIDENT_STATES = ("resolved", "closed")
STALE_TEST_DAYS = 30


async def _org_name(db: AsyncSession, org_id: uuid.UUID) -> str:
    return (await db.scalar(select(Org.name).where(Org.id == org_id))) or "Your Organization"


async def build_live_scorecard(
    db: AsyncSession, org_id: uuid.UUID
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """Return (snapshot, trend, org_name) computed from current DB state."""
    now = datetime.now(UTC)

    total = await db.scalar(
        select(func.count(func.distinct(Workload.id)))
        .select_from(Workload).join(Appliance)
        .where(Appliance.org_id == org_id)
    ) or 0
    tested = await db.scalar(
        select(func.count(func.distinct(TestRun.workload_id)))
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == org_id, TestRun.status.in_(["passed", "failed"]))
    ) or 0
    passing = await db.scalar(
        select(func.count(func.distinct(TestRun.workload_id)))
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == org_id, TestRun.status == "passed")
    ) or 0

    rrow = (await db.execute(
        select(
            func.count(TestRun.id).filter(TestRun.status == "passed").label("passed"),
            func.count(TestRun.id).filter(
                TestRun.status == "passed",
                TestRun.rto_actual_mins <= Workload.rto_target_mins,
            ).label("rto_ok"),
        )
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == org_id)
    )).one()
    total_passed = rrow.passed or 0
    rto_pct = int(rrow.rto_ok / total_passed * 100) if total_passed else 0

    active_threats = await db.scalar(
        select(func.count(ThreatFinding.id))
        .where(ThreatFinding.org_id == org_id, ThreatFinding.status == "active")
    ) or 0
    open_incidents = await db.scalar(
        select(func.count(ThreatIncident.id))
        .where(
            ThreatIncident.org_id == org_id,
            ThreatIncident.status.not_in(RESOLVED_INCIDENT_STATES),
        )
    ) or 0

    # Per-provider tested/total/pass-rate.
    prov_rows = (await db.execute(
        select(
            Workload.provider,
            func.count(func.distinct(Workload.id)).label("total"),
            func.count(func.distinct(TestRun.workload_id)).filter(
                TestRun.status.in_(["passed", "failed"])
            ).label("tested"),
            func.count(func.distinct(TestRun.workload_id)).filter(
                TestRun.status == "passed"
            ).label("passing"),
        )
        .select_from(Workload).join(Appliance)
        .outerjoin(TestRun, TestRun.workload_id == Workload.id)
        .where(Appliance.org_id == org_id)
        .group_by(Workload.provider)
    )).all()
    provider_breakdown = {
        row.provider: {
            "total": row.total,
            "tested": row.tested,
            "pass_rate": int(row.passing / row.tested * 100) if row.tested else 0,
        }
        for row in prov_rows
    }

    top_risks = await _top_risks(db, org_id, now)

    snapshot = {
        "overall_score": compute_composite_score(total, tested, passing, rto_pct),
        "workloads_total": total,
        "workloads_tested": tested,
        "workloads_passing": passing,
        "rto_compliance_pct": rto_pct,
        "active_threats": active_threats,
        "open_incidents": open_incidents,
        "provider_breakdown": provider_breakdown,
        "top_risks": top_risks,
        "snapshot_date": now.strftime("%b %Y"),
    }

    # 12-week pass-rate trend, projected onto the scorecard trend shape.
    since = now - timedelta(weeks=12)
    trend_rows = (await db.execute(
        select(TestRun.completed_at, TestRun.status)
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(
            Appliance.org_id == org_id,
            TestRun.completed_at.isnot(None),
            TestRun.completed_at >= since,
        )
    )).all()
    runs = [(ts, status == "passed") for ts, status in trend_rows]
    weekly = bucket_weekly_pass_rate(runs, weeks=12)
    trend = []
    for w in weekly:
        rate = w["pass_rate"] or 0
        n = w["runs"]
        trend.append({
            "date": w["week_ending"],
            "score": rate,
            "passing": round(rate / 100 * n),
            "total": n,
            "rto_pct": rto_pct,
        })

    return snapshot, trend, await _org_name(db, org_id)


async def _top_risks(
    db: AsyncSession, org_id: uuid.UUID, now: datetime
) -> list[dict[str, Any]]:
    """Workloads whose most recent run failed, or that are untested/stale."""
    rows = (await db.execute(
        select(
            Workload.id,
            Workload.name,
            Workload.is_protected,
            func.max(TestRun.completed_at).label("last_run"),
        )
        .select_from(Workload).join(Appliance)
        .outerjoin(TestRun, TestRun.workload_id == Workload.id)
        .where(Appliance.org_id == org_id)
        .group_by(Workload.id, Workload.name, Workload.is_protected)
    )).all()

    risks: list[dict[str, Any]] = []
    for row in rows:
        if not row.is_protected:
            continue
        if row.last_run is None:
            risks.append({
                "workload": row.name,
                "severity": "high",
                "reason": "Protected but never validated",
            })
        else:
            last = row.last_run
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            days = (now - last).days
            if days > STALE_TEST_DAYS:
                risks.append({
                    "workload": row.name,
                    "severity": "medium",
                    "reason": f"Not validated in {days} days",
                })
    # Highest severity first, then cap.
    risks.sort(key=lambda r: 0 if r["severity"] == "high" else 1)
    return risks[:5]
