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


async def load_schedules(db_session_factory) -> None:
    """Load all workload schedules from DB and register APScheduler jobs."""
    from src.models.workload import Workload
    from src.models.appliance import Appliance

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

    if not scheduler.running:
        scheduler.start()
