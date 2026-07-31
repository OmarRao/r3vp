# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Build the live context the natural-language insights query answers over.

Assembles the org-scoped figures `answer_nl_query` consumes (workload counts,
readiness score, active threats, recent failures, RTO breaches, and per-provider
pass rates) from the database, replacing the previous mock context.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.appliance import Appliance
from src.models.test_run import TestRun
from src.models.threat_scan import ThreatFinding
from src.models.workload import Workload
from src.services.readiness_scoring import compute_composite_score


async def build_query_context(db: AsyncSession, org_id: uuid.UUID) -> dict[str, Any]:
    """Return the live NL-query context for an org."""
    total = await db.scalar(
        select(func.count(func.distinct(Workload.id)))
        .select_from(Workload).join(Appliance).where(Appliance.org_id == org_id)
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
    rto_pct = int(rrow.rto_ok / rrow.passed * 100) if rrow.passed else 0

    active_threats = await db.scalar(
        select(func.count(ThreatFinding.id))
        .where(ThreatFinding.org_id == org_id, ThreatFinding.status == "active")
    ) or 0

    fail_rows = (await db.execute(
        select(Workload.name).distinct()
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == org_id, TestRun.status == "failed")
        .limit(10)
    )).all()
    recent_failures = [{"workload": name} for (name,) in fail_rows]

    breach_rows = (await db.execute(
        select(Workload.name, TestRun.rto_actual_mins, Workload.rto_target_mins)
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(
            Appliance.org_id == org_id,
            TestRun.status == "passed",
            TestRun.rto_actual_mins > Workload.rto_target_mins,
        )
        .order_by((TestRun.rto_actual_mins - Workload.rto_target_mins).desc())
        .limit(10)
    )).all()
    rto_breaches = [
        {"workload": n, "rto_actual": a, "rto_target": t} for n, a, t in breach_rows
    ]

    prov_rows = (await db.execute(
        select(
            Workload.provider,
            func.count(TestRun.id).filter(TestRun.status.in_(["passed", "failed"])).label("total"),
            func.count(TestRun.id).filter(TestRun.status == "passed").label("passed"),
        )
        .select_from(TestRun).join(Workload).join(Appliance)
        .where(Appliance.org_id == org_id)
        .group_by(Workload.provider)
    )).all()
    provider_breakdown = {
        (p or "vmware"): {"pass_rate": round(passed / total * 100) if total else 0}
        for p, total, passed in prov_rows
    }

    return {
        "workloads_total": total,
        "workloads_tested": tested,
        "overall_score": compute_composite_score(total, tested, passing, rto_pct),
        "active_threats": active_threats,
        "recent_failures": recent_failures,
        "rto_breaches": rto_breaches,
        "provider_breakdown": provider_breakdown,
    }
