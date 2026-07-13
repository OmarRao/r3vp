"""Background scheduler that triggers test runs based on workload cron schedules."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

log = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def _trigger_scheduled_run(workload_id: str, org_id: str) -> None:
    """Called by APScheduler. Creates a TestRun and enqueues the Temporal workflow."""
    from src.config import settings
    from src.db.session import async_session_factory
    from src.main import get_temporal_client
    from src.models.test_run import TestRun
    from src.models.workload import Workload

    async with async_session_factory() as db:
        workload = await db.scalar(select(Workload).where(Workload.id == uuid.UUID(workload_id)))
        if not workload:
            log.warning("scheduled run: workload not found", workload_id=workload_id)
            return

        run = TestRun(workload_id=workload.id, status="pending")
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            tc = get_temporal_client()
            wf_handle = await tc.start_workflow(
                "RecoveryTestWorkflow",
                args=[str(run.id), workload_id, str(workload.appliance_id)],
                id=str(run.id),
                task_queue=settings.temporal_task_queue,
            )
            from sqlalchemy import update
            await db.execute(
                update(TestRun).where(TestRun.id == run.id).values(
                    workflow_run_id=wf_handle.first_execution_run_id,
                    status="running",
                    started_at=datetime.now(UTC),
                )
            )
            await db.commit()
            log.info("scheduled test run triggered", run_id=str(run.id), workload_id=workload_id)
        except Exception as exc:
            # Do not leave the run orphaned in "pending"; record the failure.
            from sqlalchemy import update
            await db.execute(
                update(TestRun).where(TestRun.id == run.id).values(
                    status="failed",
                    failure_reason=f"Failed to enqueue recovery workflow: {exc}",
                    completed_at=datetime.now(UTC),
                )
            )
            await db.commit()
            log.warning("scheduled run: temporal enqueue failed", run_id=str(run.id), error=str(exc))


async def _run_report_schedule(schedule_id: str) -> None:
    """Called by APScheduler. Generates a scheduled compliance report and notifies recipients."""
    from datetime import timedelta

    from sqlalchemy import update

    from src.db.session import async_session_factory
    from src.models.report_schedule import ReportSchedule
    from src.services.notifications import send_report_delivery

    async with async_session_factory() as db:
        schedule = await db.scalar(
            select(ReportSchedule).where(ReportSchedule.id == uuid.UUID(schedule_id))
        )
        if not schedule or not schedule.enabled:
            return

        now = datetime.now(UTC)
        to_date = now.date()
        from_date = to_date - timedelta(days=schedule.period_days)
        period = f"{from_date.isoformat()} to {to_date.isoformat()}"

        try:
            await send_report_delivery(schedule.recipients or [], schedule.report_type, period)
        except Exception as exc:
            log.warning("report delivery dispatch failed", schedule_id=schedule_id, error=str(exc))

        try:
            next_run = CronTrigger.from_crontab(schedule.cron).get_next_fire_time(None, now)
        except Exception:
            next_run = now + timedelta(days=1)

        await db.execute(
            update(ReportSchedule)
            .where(ReportSchedule.id == schedule.id)
            .values(last_run_at=now, next_run_at=next_run)
        )
        await db.commit()
        log.info("scheduled report generated", schedule_id=schedule_id, report_type=schedule.report_type)


async def _run_validation_policy(policy_id: str) -> None:
    """Called by APScheduler on each policy interval. Runs the enabled micro-checks
    for the policy's workloads, records a MicroValidationRun each, and raises a
    ValidationAlert on consecutive failures."""
    import time

    from src.db.session import async_session_factory
    from src.models.appliance import Appliance
    from src.models.continuous_validation import (
        ContinuousValidationPolicy,
        MicroValidationRun,
        ValidationAlert,
    )
    from src.models.workload import Workload
    from src.services.continuous_validation import (
        build_check_results,
        evaluate_check_results,
    )

    async with async_session_factory() as db:
        policy = await db.scalar(
            select(ContinuousValidationPolicy).where(
                ContinuousValidationPolicy.id == uuid.UUID(policy_id)
            )
        )
        if not policy or not policy.enabled:
            return

        q = (
            select(Workload, Appliance.last_heartbeat)
            .join(Appliance)
            .where(Appliance.org_id == policy.org_id)
        )
        if policy.workload_scope == "specific" and policy.workload_ids:
            ids = [uuid.UUID(str(x)) for x in policy.workload_ids]
            q = q.where(Workload.id.in_(ids))
        rows = (await db.execute(q)).all()

        now = datetime.now(UTC)
        for workload, heartbeat in rows:
            start = time.monotonic()
            results = build_check_results(
                policy.checks_enabled or {},
                workload.last_backup_at,
                workload.rpo_target_mins,
                heartbeat,
                policy.check_interval_mins,
                now,
            )
            status = evaluate_check_results(results)
            passed = sum(1 for v in results.values() if v.get("status") == "pass")
            rp = results.get("restore_point_freshness", {})
            age_hours = rp.get("value_hours")
            run = MicroValidationRun(
                policy_id=policy.id,
                org_id=policy.org_id,
                workload_id=workload.id,
                workload_name=workload.name,
                status=status,
                checks_run=len(results),
                checks_passed=passed,
                check_results=results,
                restore_point_age_hours=int(age_hours) if age_hours is not None else None,
                duration_ms=round((time.monotonic() - start) * 1000),
                ran_at=now,
            )
            db.add(run)
            await db.flush()

            if policy.alert_on_failure and status == "fail":
                recent = (await db.execute(
                    select(MicroValidationRun.status)
                    .where(
                        MicroValidationRun.policy_id == policy.id,
                        MicroValidationRun.workload_id == workload.id,
                    )
                    .order_by(MicroValidationRun.ran_at.desc())
                    .limit(policy.consecutive_failures_before_alert)
                )).scalars().all()
                consecutive = 0
                for s in recent:
                    if s != "pass":
                        consecutive += 1
                    else:
                        break
                if consecutive >= policy.consecutive_failures_before_alert:
                    existing = await db.scalar(
                        select(ValidationAlert).where(
                            ValidationAlert.policy_id == policy.id,
                            ValidationAlert.workload_id == workload.id,
                            ValidationAlert.resolved.is_(False),
                        )
                    )
                    if not existing:
                        db.add(ValidationAlert(
                            policy_id=policy.id,
                            org_id=policy.org_id,
                            workload_id=workload.id,
                            workload_name=workload.name,
                            alert_type="consecutive_failures",
                            severity="high",
                            detail=f"{consecutive} consecutive failing micro-validations",
                            created_at=now,
                        ))
                        run.alert_sent = True

        await db.commit()
        log.info("continuous validation policy run", policy_id=policy_id, workloads=len(rows))


async def load_schedules(db_session_factory) -> None:
    """Load workload and report schedules from DB and register APScheduler jobs."""
    from src.models.appliance import Appliance
    from src.models.report_schedule import ReportSchedule
    from src.models.workload import Workload

    scheduler = get_scheduler()
    scheduler.remove_all_jobs()

    async with db_session_factory() as db:
        rows = await db.execute(
            select(Workload, Appliance.org_id)
            .join(Appliance)
            .where(Workload.schedule_cron.isnot(None))
        )
        for workload, org_id in rows.all():
            try:
                trigger = CronTrigger.from_crontab(workload.schedule_cron)
                scheduler.add_job(
                    _trigger_scheduled_run,
                    trigger,
                    args=[str(workload.id), str(org_id)],
                    id=f"workload-{workload.id}",
                    replace_existing=True,
                )
                log.info("schedule registered", workload=workload.name, cron=workload.schedule_cron)
            except Exception as exc:
                log.warning("invalid cron expression", workload_id=str(workload.id), error=str(exc))

        report_rows = await db.execute(
            select(ReportSchedule).where(ReportSchedule.enabled.is_(True))
        )
        for schedule in report_rows.scalars().all():
            try:
                trigger = CronTrigger.from_crontab(schedule.cron)
                scheduler.add_job(
                    _run_report_schedule,
                    trigger,
                    args=[str(schedule.id)],
                    id=f"report-{schedule.id}",
                    replace_existing=True,
                )
                log.info("report schedule registered", name=schedule.name, cron=schedule.cron)
            except Exception as exc:
                log.warning("invalid report cron expression", schedule_id=str(schedule.id), error=str(exc))

        from src.models.continuous_validation import ContinuousValidationPolicy
        policy_rows = await db.execute(
            select(ContinuousValidationPolicy).where(ContinuousValidationPolicy.enabled.is_(True))
        )
        for policy in policy_rows.scalars().all():
            try:
                scheduler.add_job(
                    _run_validation_policy,
                    IntervalTrigger(minutes=max(1, policy.check_interval_mins)),
                    args=[str(policy.id)],
                    id=f"cv-policy-{policy.id}",
                    replace_existing=True,
                )
                log.info("cv policy registered", name=policy.name, interval=policy.check_interval_mins)
            except Exception as exc:
                log.warning("cv policy registration failed", policy_id=str(policy.id), error=str(exc))

    if not scheduler.running:
        scheduler.start()
