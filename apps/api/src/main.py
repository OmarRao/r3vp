from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from temporalio.client import Client, TLSConfig

from src.config import settings
from src.routers import (
    api_keys,
    appliances,
    audit,
    compliance_frameworks,
    continuous_validation,
    evidence,
    executive,
    fleet,
    insights,
    integrations,
    mssp,
    notifications,
    onboarding,
    portal_appliances,
    readiness,
    report_schedules,
    reports,
    runbooks,
    sso,
    team,
    test_runs,
    users,
    workloads,
)
from src.routers.multicloud import router as multicloud_router
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
        tls = None
        if settings.temporal_cert_path:
            with open(settings.temporal_cert_path, "rb") as cert_f:
                client_cert = cert_f.read()
            with open(settings.temporal_key_path, "rb") as key_f:
                client_private_key = key_f.read()
            tls = TLSConfig(client_cert=client_cert, client_private_key=client_private_key)
        _temporal_client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            tls=tls,
        )
        log.info("temporal connected", address=settings.temporal_address)
    except Exception as exc:
        log.warning("temporal unavailable at startup", error=str(exc))

    try:
        from src.db.session import async_session_factory
        from src.scheduler import get_scheduler, load_schedules
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
app.include_router(report_schedules.router, prefix="/v1/report-schedules", tags=["report-schedules"])
app.include_router(threat_intel_router)
app.include_router(multicloud_router)
app.include_router(team.router, prefix="/v1/team", tags=["team"])
app.include_router(api_keys.router, prefix="/v1/api-keys", tags=["api-keys"])
app.include_router(sso.router, prefix="/v1/sso", tags=["sso"])
app.include_router(executive.router, prefix="/v1/executive", tags=["executive"])
app.include_router(integrations.router, prefix="/v1/integrations", tags=["integrations"])
app.include_router(insights.router, prefix="/v1/insights", tags=["insights"])
app.include_router(runbooks.router, prefix="/v1/runbooks", tags=["runbooks"])
app.include_router(onboarding.router, prefix="/v1/onboarding", tags=["onboarding"])
app.include_router(fleet.router, prefix="/v1/fleet", tags=["fleet"])
app.include_router(mssp.router, prefix="/v1/mssp", tags=["mssp"])
app.include_router(compliance_frameworks.router, prefix="/v1/compliance-frameworks", tags=["compliance-frameworks"])
app.include_router(continuous_validation.router, prefix="/v1/continuous-validation", tags=["continuous-validation"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
