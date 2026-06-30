"""Integrations marketplace: CRUD and manual trigger."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.integration import Integration, IntegrationEventLog
from src.services.integrations import dispatch_event
from src.services.rbac import require_permission

router = APIRouter()

VALID_TYPES = {"servicenow", "jira", "pagerduty", "splunk", "qradar", "sentinel"}
VALID_EVENTS = {"sla_breach", "test_failed", "threat_detected", "incident_created"}

INTEGRATION_CATALOG = [
    {"type": "servicenow", "name": "ServiceNow", "description": "Create CMDB incidents and update CI records on SLA breach or test failure", "category": "ITSM"},
    {"type": "jira", "name": "Jira", "description": "Open Jira issues when recovery tests fail or RTO targets are breached", "category": "ITSM"},
    {"type": "pagerduty", "name": "PagerDuty", "description": "Trigger PagerDuty alerts for critical recovery failures and active threats", "category": "Alerting"},
    {"type": "splunk", "name": "Splunk", "description": "Push recovery events and threat findings to Splunk via HEC", "category": "SIEM"},
    {"type": "qradar", "name": "IBM QRadar", "description": "Send CEF syslog events for recovery test results and threat detections", "category": "SIEM"},
    {"type": "sentinel", "name": "Microsoft Sentinel", "description": "Stream R3VP events to Azure Sentinel Log Analytics workspace", "category": "SIEM"},
]


class CreateIntegrationRequest(BaseModel):
    integration_type: str
    name: str
    config: dict
    trigger_events: list[str]


@router.get("/catalog")
async def get_catalog():
    return INTEGRATION_CATALOG


@router.get("")
async def list_integrations(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "settings:read")
    rows = await db.execute(
        select(Integration)
        .where(Integration.org_id == user.org_id)
        .order_by(Integration.created_at.desc())
    )
    return [
        {
            "id": str(i.id),
            "type": i.integration_type,
            "name": i.name,
            "trigger_events": i.trigger_events,
            "enabled": i.enabled,
            "last_triggered_at": i.last_triggered_at.isoformat() if i.last_triggered_at else None,
            "last_status": i.last_status,
        }
        for i in rows.scalars().all()
    ]


@router.post("", status_code=201)
async def create_integration(
    body: CreateIntegrationRequest,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "settings:write")
    if body.integration_type not in VALID_TYPES:
        raise HTTPException(400, f"integration_type must be one of: {', '.join(sorted(VALID_TYPES))}")
    invalid_events = [e for e in body.trigger_events if e not in VALID_EVENTS]
    if invalid_events:
        raise HTTPException(400, f"Invalid trigger_events: {invalid_events}")

    integration = Integration(
        org_id=user.org_id,
        integration_type=body.integration_type,
        name=body.name,
        config=body.config,
        trigger_events=body.trigger_events,
        created_by=getattr(user, "user_id", None),
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return {"id": str(integration.id), "type": integration.integration_type, "name": integration.name}


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "settings:write")
    integration = await db.scalar(
        select(Integration).where(Integration.id == integration_id, Integration.org_id == user.org_id)
    )
    if not integration:
        raise HTTPException(404, "Integration not found")

    test_payload = {"workload": "test-workload-01", "severity": "medium", "message": "R3VP integration test"}
    success, error, ms = await dispatch_event(
        integration.integration_type,
        integration.config,
        "test_event",
        test_payload,
    )
    return {"success": success, "error": error, "response_ms": ms}


@router.patch("/{integration_id}/toggle")
async def toggle_integration(
    integration_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "settings:write")
    integration = await db.scalar(
        select(Integration).where(Integration.id == integration_id, Integration.org_id == user.org_id)
    )
    if not integration:
        raise HTTPException(404, "Integration not found")
    integration.enabled = not integration.enabled
    await db.commit()
    return {"enabled": integration.enabled}


@router.delete("/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "settings:write")
    integration = await db.scalar(
        select(Integration).where(Integration.id == integration_id, Integration.org_id == user.org_id)
    )
    if not integration:
        raise HTTPException(404, "Integration not found")
    await db.delete(integration)
    await db.commit()


@router.get("/{integration_id}/logs")
async def get_event_logs(
    integration_id: uuid.UUID,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "settings:read")
    rows = await db.execute(
        select(IntegrationEventLog)
        .where(IntegrationEventLog.integration_id == integration_id, IntegrationEventLog.org_id == user.org_id)
        .order_by(IntegrationEventLog.triggered_at.desc())
        .limit(50)
    )
    return [
        {
            "id": str(log.id),
            "event_type": log.event_type,
            "status": log.status,
            "error_detail": log.error_detail,
            "triggered_at": log.triggered_at.isoformat(),
            "response_ms": log.response_ms,
        }
        for log in rows.scalars().all()
    ]
