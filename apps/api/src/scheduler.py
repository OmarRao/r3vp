"""Background scheduler that triggers test runs based on workload cron schedules."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
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
    from src.db.session import async_session_factory
    from src.models.test_run import TestRun
    from src.models.workload import Workload
    from src.main import get_temporal_client
    from src.config import settings

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
                    started_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()
            log.info("scheduled test run triggered", run_id=str(run.id), workload_id=workload_id)
        except Exception as exc:
            log.warning("scheduled run: temporal enqueue failed", error=str(exc))


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

        now = datetime.now(timezone.utc)
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


async def load_schedules(db_session_factory) -> None:
    """Load workload and report schedules from DB and register APScheduler jobs."""
    from src.models.workload import Workload
    from src.models.appliance import Appliance
    from src.models.report_schedule import ReportSchedule

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

    if not scheduler.running:
        scheduler.start()
