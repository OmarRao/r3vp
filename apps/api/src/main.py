from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.routers import appliances, workloads, test_runs, readiness, evidence, audit

log = structlog.get_logger()

app = FastAPI(
    title="R3VP API",
    version="0.1.0",
    description="Ransomware Readiness & Recovery Validation Platform — SaaS API",
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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
