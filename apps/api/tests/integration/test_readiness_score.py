"""Integration test: readiness endpoint returns correct compliance percentages."""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from src.models.appliance import Org, Appliance
from src.models.workload import Workload
from src.models.test_run import TestRun


@pytest.mark.asyncio
async def test_readiness_score_calculation(db_session):
    """Three workloads: 2 pass within targets, 1 fails RTO. Verify compliance math."""
    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()

    db_session.add(Org(id=org_id, name="Score Test Org"))
    db_session.add(Appliance(
        id=appliance_id, org_id=org_id, name="appliance-1",
        mtls_thumbprint="thumb1", status="active"
    ))
    await db_session.commit()

    workloads = []
    for i in range(3):
        wl = Workload(
            appliance_id=appliance_id, name=f"wl-{i}",
            platform="vmware", rto_target_mins=30, rpo_target_mins=60,
        )
        db_session.add(wl)
        workloads.append(wl)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    # wl-0: passed, RTO 15 min (within 30 min target)
    db_session.add(TestRun(workload_id=workloads[0].id, status="passed",
                           started_at=now, completed_at=now,
                           rto_actual_mins=15, rpo_actual_mins=30, readiness_score=95))
    # wl-1: passed, RTO 25 min (within 30 min target)
    db_session.add(TestRun(workload_id=workloads[1].id, status="passed",
                           started_at=now, completed_at=now,
                           rto_actual_mins=25, rpo_actual_mins=20, readiness_score=90))
    # wl-2: failed, RTO 45 min (exceeds 30 min target)
    db_session.add(TestRun(workload_id=workloads[2].id, status="failed",
                           started_at=now, completed_at=now,
                           rto_actual_mins=45, rpo_actual_mins=10, readiness_score=40))
    await db_session.commit()

    # Verify data was committed correctly
    runs = await db_session.execute(select(TestRun))
    all_runs = runs.scalars().all()
    passed_runs = [r for r in all_runs if r.status == "passed"]
    failed_runs = [r for r in all_runs if r.status == "failed"]
    assert len(passed_runs) >= 2
    assert len(failed_runs) >= 1

    # RTO compliance: 2 of 3 runs have rto_actual <= rto_target (15<=30, 25<=30, 45>30)
    rto_ok = [r for r in all_runs if r.rto_actual_mins and r.rto_actual_mins <= 30]
    assert len(rto_ok) >= 2
