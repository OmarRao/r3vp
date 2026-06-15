"""Business logic for appliance registration, heartbeat, and command dispatch."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.appliance import Appliance, Org
from src.models.test_run import TestRun, AuditEvent


async def register_appliance(
    db: AsyncSession,
    org_id: uuid.UUID,
    appliance_id: uuid.UUID,
    name: str,
    mtls_thumbprint: str,
    version: str | None,
) -> Appliance:
    """Upsert appliance record. Creates org row if it doesn't exist yet."""
    # Ensure org exists (auto-create for MVP; production requires pre-provisioning)
    org_exists = await db.scalar(select(Org.id).where(Org.id == org_id))
    if not org_exists:
        db.add(Org(id=org_id, name=f"org-{org_id}"))

    stmt = (
        pg_insert(Appliance)
        .values(
            id=appliance_id,
            org_id=org_id,
            name=name,
            mtls_thumbprint=mtls_thumbprint,
            version=version,
            status="active",
            last_heartbeat=datetime.now(timezone.utc),
        )
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "mtls_thumbprint": mtls_thumbprint,
                "version": version,
                "status": "active",
                "last_heartbeat": datetime.now(timezone.utc),
            },
        )
        .returning(Appliance)
    )
    result = await db.execute(stmt)
    appliance = result.scalar_one()

    await _audit(db, org_id=org_id, actor_id=appliance_id, actor_type="appliance",
                 event_type="appliance.registered",
                 resource_id=appliance_id, detail={"version": version})
    await db.commit()
    return appliance


async def record_heartbeat(
    db: AsyncSession,
    appliance_id: uuid.UUID,
    version: str,
) -> datetime:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Appliance)
        .where(Appliance.id == appliance_id)
        .values(last_heartbeat=now, version=version)
    )
    await db.commit()
    return now


async def get_pending_commands(
    db: AsyncSession,
    appliance_id: uuid.UUID,
) -> list[dict]:
    """Return test runs in 'pending' state for workloads on this appliance."""
    from src.models.workload import Workload

    rows = await db.execute(
        select(TestRun)
        .join(Workload, TestRun.workload_id == Workload.id)
        .where(
            Workload.appliance_id == appliance_id,
            TestRun.status == "pending",
        )
    )
    runs = rows.scalars().all()
    return [
        {
            "type": "run_recovery_test",
            "run_id": str(r.id),
            "workload_id": str(r.workload_id),
        }
        for r in runs
    ]


async def accept_inventory_sync(
    db: AsyncSession,
    appliance_id: uuid.UUID,
    org_id: uuid.UUID,
    vms: list[dict],
) -> int:
    """Upsert workloads discovered by the appliance. Returns count upserted."""
    from src.models.workload import Workload
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    upserted = 0
    for vm in vms:
        stmt = (
            pg_insert(Workload)
            .values(
                id=uuid.uuid4(),
                appliance_id=appliance_id,
                name=vm.get("name", "unknown"),
                platform=vm.get("platform", "vmware"),
                os_type=vm.get("os_type"),
                veeam_object_id=vm.get("object_id"),
                vcenter_moref=vm.get("moref"),
                is_protected=bool(vm.get("is_protected", False)),
                last_backup_at=vm.get("last_backup"),
            )
            .on_conflict_do_update(
                constraint="uq_workloads_appliance_veeam",
                set_={
                    "name": vm.get("name", "unknown"),
                    "is_protected": bool(vm.get("is_protected", False)),
                    "last_backup_at": vm.get("last_backup"),
                },
            )
        )
        await db.execute(stmt)
        upserted += 1

    await _audit(db, org_id=org_id, actor_id=appliance_id, actor_type="appliance",
                 event_type="inventory.synced", detail={"vm_count": upserted})
    await db.commit()
    return upserted


async def update_run_progress(
    db: AsyncSession,
    run_id: uuid.UUID,
    step: str,
    status: str,
    detail: dict,
) -> None:
    from src.models.test_run import TestRunStep
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    now = datetime.now(timezone.utc)
    await db.execute(
        pg_insert(TestRunStep)
        .values(run_id=run_id, step_name=step, status=status,
                started_at=now if status == "running" else None,
                ended_at=now if status in ("passed", "failed") else None,
                detail=detail)
        .on_conflict_do_nothing()
    )
    # Also flip the parent run to running if it's still pending
    if status == "running":
        await db.execute(
            update(TestRun)
            .where(TestRun.id == run_id, TestRun.status == "pending")
            .values(status="running", started_at=now)
        )
    await db.commit()


async def finalise_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    passed: bool,
    rto_actual_mins: int,
    rpo_actual_mins: int,
    readiness_score: int,
    failure_reason: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(TestRun)
        .where(TestRun.id == run_id)
        .values(
            status="passed" if passed else "failed",
            completed_at=now,
            rto_actual_mins=rto_actual_mins,
            rpo_actual_mins=rpo_actual_mins,
            readiness_score=readiness_score,
            failure_reason=failure_reason,
        )
    )
    await db.commit()

    # Send breach notifications (best-effort)
    try:
        from src.models.workload import Workload
        from src.models.appliance import Appliance as App
        from src.services.notifications import send_breach_notifications
        run_row = await db.scalar(select(TestRun).where(TestRun.id == run_id))
        if run_row:
            wl = await db.scalar(
                select(Workload).where(Workload.id == run_row.workload_id)
            )
            if wl:
                app_row = await db.scalar(select(App).where(App.id == wl.appliance_id))
                org_id = app_row.org_id if app_row else None
                if org_id:
                    await send_breach_notifications(
                        db, org_id=org_id,
                        workload_name=wl.name, run_id=str(run_id),
                        rto_target=wl.rto_target_mins, rto_actual=rto_actual_mins,
                        rpo_target=wl.rpo_target_mins, rpo_actual=rpo_actual_mins,
                        passed=passed,
                    )
    except Exception as exc:
        import structlog as _sl
        _sl.get_logger().warning("notification dispatch error", error=str(exc))


async def _audit(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    actor_type: str,
    event_type: str,
    resource_id: uuid.UUID | None = None,
    detail: dict | None = None,
) -> None:
    db.add(AuditEvent(
        org_id=org_id,
        actor_id=actor_id,
        actor_type=actor_type,
        event_type=event_type,
        resource_id=resource_id,
        detail=detail or {},
    ))
