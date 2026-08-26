# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from temporalio.client import Client, TLSConfig

from src.config import settings
from src.http_hardening import SecurityHeadersMiddleware
from src.rate_limit import FixedWindowRateLimiter, RateLimitMiddleware
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

    # The temporalio Client has no explicit close(); its connection is managed
    # by the SDK and released on garbage collection, so no teardown is needed.


app = FastAPI(
    title="R3VP API",
    version="1.0.0",
    description="Ransomware Readiness and Recovery Validation Platform - SaaS API",
    lifespan=lifespan,
)

# Compress large JSON responses (dashboards, reports, OpenAPI) for clients that
# accept gzip; small responses are left uncompressed.
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.r3vp.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers + per-request correlation id on every response.
app.add_middleware(SecurityHeadersMiddleware)

# Per-client rate limiting (added last so it runs first, before request work).
if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        limiter=FixedWindowRateLimiter(settings.rate_limit_per_minute, window_seconds=60),
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


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/live", tags=["health"])
async def live() -> dict:
    """Liveness probe: the process is up and serving."""
    return {"status": "alive"}


@app.get("/ready", tags=["health"])
async def ready() -> JSONResponse:
    """Readiness probe: the API can reach its database."""
    from src.db.session import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except Exception as exc:  # noqa: BLE001 - report any DB failure as not-ready
        log.warning("readiness_check_failed", error=str(exc))
        return JSONResponse({"status": "not ready"}, status_code=503)


# Prometheus metrics at /metrics (request counts, latency histograms, in-flight).
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
