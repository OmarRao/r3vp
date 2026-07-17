"""Seed a self-contained demo dataset for R3VP.

Creates one organization ("Northwind Demo") with a full, internally consistent
graph so every shipped feature is immediately demonstrable against a live
database: readiness scoring and 12-week trend, AI insights (RTO prediction,
risk ranking, NL query), threat analysis, integrations, and RBAC roles.

Usage (from apps/api, with DATABASE_URL pointing at a migrated database):

    uv run python -m src.scripts.seed_demo            # seed (no-op if present)
    uv run python -m src.scripts.seed_demo --reset    # wipe demo org, reseed

The org uses a fixed UUID so the script is idempotent and safe to re-run. It
only ever touches rows belonging to that demo org; other data is untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from src.db.session import AsyncSessionLocal
from src.models.appliance import Appliance, Org
from src.models.integration import Integration
from src.models.test_run import HealthCheckResult, TestRun, TestRunStep, User
from src.models.threat_scan import ThreatFinding, ThreatScan
from src.models.workload import Workload

# Fixed namespace so every entity id is deterministic across runs.
DEMO_ORG_ID = uuid.UUID("d3305e00-0000-4000-8000-000000000001")
_NS = uuid.UUID("d3305e00-0000-4000-8000-0000000000ff")


def _id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_NS, ":".join(parts))


def _now() -> datetime:
    return datetime.now(UTC)


ROLES = ["owner", "admin", "operator", "auditor", "viewer"]

# (name, platform, os_type, protected, rto_target_mins, rpo_target_mins, tier)
WORKLOADS = [
    ("dc01-primary", "vmware", "windows", True, 60, 15, "tier1"),
    ("sql-prod-01", "vmware", "windows", True, 120, 15, "tier1"),
    ("app-web-01", "vmware", "linux", True, 240, 60, "tier2"),
    ("app-web-02", "vmware", "linux", True, 240, 60, "tier2"),
    ("file-server-01", "hyperv", "windows", True, 480, 120, "tier2"),
    ("exchange-01", "vmware", "windows", True, 120, 30, "tier1"),
    ("erp-app-01", "vmware", "linux", True, 240, 60, "tier1"),
    ("build-agent-03", "vmware", "linux", False, None, None, "tier3"),
    ("legacy-billing", "physical", "windows", True, 720, 240, "tier3"),
    ("k8s-node-07", "vmware", "linux", True, 240, 60, "tier2"),
]


async def _demo_org_present(session) -> bool:
    return (await session.get(Org, DEMO_ORG_ID)) is not None


async def _reset(session) -> None:
    """Delete every row belonging to the demo org, child tables first."""
    appliance_ids = (
        await session.execute(select(Appliance.id).where(Appliance.org_id == DEMO_ORG_ID))
    ).scalars().all()
    workload_ids = []
    if appliance_ids:
        workload_ids = (
            await session.execute(
                select(Workload.id).where(Workload.appliance_id.in_(appliance_ids))
            )
        ).scalars().all()
    run_ids = []
    if workload_ids:
        run_ids = (
            await session.execute(
                select(TestRun.id).where(TestRun.workload_id.in_(workload_ids))
            )
        ).scalars().all()

    if run_ids:
        await session.execute(delete(TestRunStep).where(TestRunStep.run_id.in_(run_ids)))
        await session.execute(delete(HealthCheckResult).where(HealthCheckResult.run_id.in_(run_ids)))
        await session.execute(delete(TestRun).where(TestRun.id.in_(run_ids)))
    if workload_ids:
        await session.execute(delete(Workload).where(Workload.id.in_(workload_ids)))
    await session.execute(delete(ThreatFinding).where(ThreatFinding.org_id == DEMO_ORG_ID))
    await session.execute(delete(ThreatScan).where(ThreatScan.org_id == DEMO_ORG_ID))
    await session.execute(delete(Integration).where(Integration.org_id == DEMO_ORG_ID))
    if appliance_ids:
        await session.execute(delete(Appliance).where(Appliance.id.in_(appliance_ids)))
    await session.execute(delete(User).where(User.org_id == DEMO_ORG_ID))
    await session.execute(delete(Org).where(Org.id == DEMO_ORG_ID))
    await session.commit()


async def _seed(session) -> dict:
    rng = random.Random(42)
    now = _now()

    org = Org(id=DEMO_ORG_ID, name="Northwind Demo")
    session.add(org)

    for role in ROLES:
        session.add(
            User(
                id=_id("user", role),
                org_id=DEMO_ORG_ID,
                auth0_sub=f"demo|northwind-{role}",
                email=f"{role}@northwind.example",
                role=role,
            )
        )

    appliance = Appliance(
        id=_id("appliance", "primary"),
        org_id=DEMO_ORG_ID,
        name="northwind-appliance-01",
        version="1.4.0",
        last_heartbeat=now - timedelta(minutes=3),
        mtls_thumbprint=hashlib.sha256(b"northwind-demo-appliance").hexdigest(),
        status="active",
    )
    session.add(appliance)
    await session.flush()

    n_runs = 0
    for name, platform, os_type, protected, rto_t, rpo_t, tier in WORKLOADS:
        wl = Workload(
            id=_id("workload", name),
            appliance_id=appliance.id,
            name=name,
            platform=platform,
            os_type=os_type,
            is_protected=protected,
            last_backup_at=now - timedelta(hours=rng.randint(1, 30)),
            rto_target_mins=rto_t,
            rpo_target_mins=rpo_t,
            schedule_cron="0 2 * * *",
            tags={"tier": tier, "env": "prod"},
            provider=platform,
        )
        session.add(wl)
        if not protected:
            continue

        # 12 weeks of weekly validation runs, trending toward faster RTO.
        for week in range(12, 0, -1):
            started = now - timedelta(weeks=week, hours=rng.randint(0, 6))
            # failure rate declines over time; tier3 is flakier.
            base_fail = 0.28 if tier == "tier3" else 0.14
            fail_p = base_fail * (week / 12.0)
            failed = rng.random() < fail_p
            improve = (12 - week) / 12.0
            rto_actual = max(5, int((rto_t or 120) * (1.15 - 0.35 * improve) * rng.uniform(0.85, 1.1)))
            duration = timedelta(minutes=rto_actual)
            run = TestRun(
                id=_id("run", name, str(week)),
                workload_id=wl.id,
                triggered_by=_id("user", "operator"),
                restore_point=started - timedelta(minutes=rng.randint(5, 60)),
                started_at=started,
                completed_at=started + duration,
                status="failed" if failed else "passed",
                rto_actual_mins=None if failed else rto_actual,
                rpo_actual_mins=None if failed else max(1, int((rpo_t or 60) * rng.uniform(0.4, 0.95))),
                readiness_score=None if failed else rng.randint(82, 99),
                failure_reason="Guest OS heartbeat timeout during boot validation" if failed else None,
                evidence_path=f"s3://r3vp-evidence/northwind/{name}/wk{week}/",
            )
            session.add(run)
            await session.flush()
            for step_name in ("mount_restore_point", "boot_isolated", "os_health", "app_health", "teardown"):
                step_failed = failed and step_name == "os_health"
                session.add(
                    TestRunStep(
                        run_id=run.id,
                        step_name=step_name,
                        status="failed" if step_failed else "passed",
                        started_at=started,
                        ended_at=started + timedelta(minutes=rng.randint(1, 10)),
                        detail={},
                    )
                )
                if step_failed:
                    break
            for check in ("ping", "service_up", "disk_mounted"):
                session.add(
                    HealthCheckResult(
                        run_id=run.id,
                        check_name=check,
                        passed=not failed,
                        output="ok" if not failed else "no response",
                    )
                )
            n_runs += 1

    # Integrations
    for itype, iname, cfg in [
        ("slack", "SecOps Slack", {"webhook_url": "https://hooks.slack.com/services/DEMO/CHANNEL"}),
        ("pagerduty", "On-call Escalation", {"routing_key": "DEMOROUTINGKEY0123456789012"}),
        ("webhook", "SIEM Forwarder", {"url": "https://siem.northwind.example/ingest"}),
    ]:
        session.add(
            Integration(
                id=_id("integration", itype),
                org_id=DEMO_ORG_ID,
                integration_type=itype,
                name=iname,
                config=cfg,
                trigger_events=["test_run.failed", "threat.detected"],
                enabled=True,
                last_triggered_at=now - timedelta(days=rng.randint(1, 5)),
                last_status="ok",
                created_by=_id("user", "admin"),
            )
        )

    # Threat scans + findings (one clean, one with detections)
    for offset, crit, high in [(20, 0, 0), (2, 1, 2)]:
        started = now - timedelta(days=offset)
        scan = ThreatScan(
            id=_id("scan", str(offset)),
            org_id=DEMO_ORG_ID,
            appliance_id=appliance.id,
            scan_id=f"scan-northwind-{offset}",
            started_at=started,
            completed_at=started + timedelta(minutes=18),
            hosts_scanned=len(WORKLOADS),
            signatures_checked=14230,
            yara_rules_checked=312,
            critical_count=crit,
            high_count=high,
            medium_count=0,
            low_count=0,
        )
        session.add(scan)
        await session.flush()
        if crit or high:
            for sev, tname, ttype, technique, host in [
                ("critical", "LockBit encryptor artifact", "ransomware", "T1486", "legacy-billing"),
                ("high", "Mass file rename (.locked)", "ransomware", "T1486", "file-server-01"),
                ("high", "Suspicious ransom note README_RECOVER.txt", "ransomware", "T1486", "file-server-01"),
            ][: crit + high]:
                session.add(
                    ThreatFinding(
                        scan_id=scan.id,
                        org_id=DEMO_ORG_ID,
                        signature_id=f"YARA-{technique}",
                        threat_name=tname,
                        threat_type=ttype,
                        severity=sev,
                        host=host,
                        indicator_type="file",
                        indicator_value=f"/mnt/restore/{host}/suspicious.bin",
                        context={"entropy": 7.98},
                        mitre_technique=technique,
                        status="active",
                        detected_at=started + timedelta(minutes=9),
                    )
                )

    await session.commit()
    return {"org": "Northwind Demo", "org_id": str(DEMO_ORG_ID), "users": len(ROLES),
            "workloads": len(WORKLOADS), "test_runs": n_runs}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed R3VP demo data")
    parser.add_argument("--reset", action="store_true", help="wipe the demo org before seeding")
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        if await _demo_org_present(session):
            if not args.reset:
                print("Demo org already present. Re-run with --reset to rebuild.")
                return
            print("Resetting existing demo org...")
            await _reset(session)
        summary = await _seed(session)

    print("Seeded demo dataset:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
