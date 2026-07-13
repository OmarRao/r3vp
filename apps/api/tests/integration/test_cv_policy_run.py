"""Integration test: the continuous-validation policy job over real Postgres.

Seeds a policy + a workload with a stale restore point, runs the scheduler job
twice, and asserts micro-validation runs are recorded and a consecutive-failure
alert is raised.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.models.appliance import Appliance, Org
from src.models.continuous_validation import (
    ContinuousValidationPolicy,
    MicroValidationRun,
    ValidationAlert,
)
from src.models.workload import Workload
from src.scheduler import _run_validation_policy

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_policy_run_records_runs_and_alerts(db_engine, db_session, monkeypatch):
    # The job opens its own session via async_session_factory; point that at the
    # test engine so it shares this database.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    test_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    monkeypatch.setattr("src.db.session.async_session_factory", test_factory, raising=False)

    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="CV Org"))
    # Appliance heartbeat is fresh; the failing signal is the stale restore point.
    db_session.add(Appliance(id=appliance_id, org_id=org_id, name="ap-1",
                             mtls_thumbprint="t", status="active",
                             last_heartbeat=datetime.now(UTC)))
    await db_session.commit()

    wl = Workload(appliance_id=appliance_id, name="stale-vm", platform="vmware",
                  rto_target_mins=60, rpo_target_mins=60,
                  last_backup_at=datetime.now(UTC) - timedelta(hours=10))  # way past RPO
    db_session.add(wl)
    await db_session.commit()

    policy = ContinuousValidationPolicy(
        org_id=org_id, name="Tier 1", enabled=True, check_interval_mins=15,
        workload_scope="all",
        checks_enabled={"restore_point_freshness": True, "rpo_compliance": True,
                        "agent_heartbeat": True, "mount_check": True},
        alert_on_failure=True, consecutive_failures_before_alert=2,
    )
    db_session.add(policy)
    await db_session.commit()
    policy_id = str(policy.id)

    # Run twice to cross the consecutive-failure threshold.
    await _run_validation_policy(policy_id)
    await _run_validation_policy(policy_id)

    runs = (await db_session.execute(
        select(MicroValidationRun).where(MicroValidationRun.policy_id == policy.id)
    )).scalars().all()
    assert len(runs) == 2
    assert all(r.status == "fail" for r in runs)  # stale RP -> fail
    # mount_check must be recorded as skipped, not counted as a failure source only.
    assert runs[0].check_results["mount_check"]["status"] == "skipped"

    alerts = (await db_session.execute(
        select(ValidationAlert).where(ValidationAlert.policy_id == policy.id)
    )).scalars().all()
    assert len(alerts) == 1
    assert alerts[0].alert_type == "consecutive_failures"
    assert alerts[0].workload_name == "stale-vm"
