from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from temporalio.client import Client, TLSConfig

from src.config import settings
from src.routers import appliances, workloads, test_runs, readiness, evidence, audit, notifications, users, portal_appliances, reports
from src.routers.threat_intel import router as threat_intel_router

log = structlog.get_logger()

_temporal_client: Client | None = None


def get_temporal_client() -> Client:
    if _temporal_client is None:
        raise RuntimeError("Temporal client not initialised")
    return _temporal_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _temporal_client
    try:
        tls = TLSConfig(
            client_cert=open(settings.temporal_cert_path, "rb").read(),
            client_private_key=open(settings.temporal_key_path, "rb").read(),
        ) if settings.temporal_cert_path else None
        _temporal_client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            tls=tls,
        )
        log.info("temporal connected", address=settings.temporal_address)
    except Exception as exc:
        log.warning("temporal unavailable at startup", error=str(exc))

    try:
        from src.scheduler import load_schedules, get_scheduler
        from src.db.session import async_session_factory
        await load_schedules(async_session_factory)
    except Exception as exc:
        log.warning("scheduler startup failed", error=str(exc))

    yield

    try:
        from src.scheduler import get_scheduler
        sched = get_scheduler()
        if sched.running:
            sched.shutdown(wait=False)
    except Exception:
        pass

    if _temporal_client:
        await _temporal_client.close()


app = FastAPI(
    title="R3VP API",
    version="0.2.0",
    description="Ransomware Readiness and Recovery Validation Platform - SaaS API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.r3vp.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(appliances.router, prefix="/v1/appliance", tags=["Appliance"])
app.include_router(workloads.router, prefix="/v1/workloads", tags=["Workloads"])
app.include_router(test_runs.router, prefix="/v1/test-runs", tags=["Test Runs"])
app.include_router(readiness.router, prefix="/v1/dashboard", tags=["Dashboard"])
app.include_router(evidence.router, prefix="/v1/evidence", tags=["Evidence"])
app.include_router(audit.router, prefix="/v1/audit-log", tags=["Audit"])
app.include_router(notifications.router, prefix="/v1/notifications", tags=["Notifications"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"])
app.include_router(portal_appliances.router, prefix="/v1/portal/appliances", tags=["Portal Appliances"])
app.include_router(reports.router, prefix="/v1/reports", tags=["Reports"])
app.include_router(threat_intel_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
