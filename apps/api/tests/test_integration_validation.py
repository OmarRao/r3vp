"""Unit tests for integration config validation (pure) + the create 400 path."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.services.integrations.validation import validate_integration_config


def test_valid_configs_pass():
    assert validate_integration_config("pagerduty", {"routing_key": "R123"}) == []
    assert validate_integration_config("sentinel", {"workspace_id": "w", "shared_key": "k"}) == []
    assert validate_integration_config("servicenow", {
        "instance_url": "https://x.service-now.com", "api_token": "t"}) == []


def test_missing_required_fields_reported():
    errors = validate_integration_config("jira", {"base_url": "https://j.example"})
    assert any("api_token" in e for e in errors)
    assert any("email" in e for e in errors)
    assert any("project_key" in e for e in errors)


def test_non_url_rejected():
    errors = validate_integration_config("servicenow", {"instance_url": "x.service-now.com", "api_token": "t"})
    assert any("http" in e for e in errors)


def test_qradar_port_validation():
    assert any("number" in e for e in validate_integration_config(
        "qradar", {"syslog_host": "h", "syslog_port": "abc"}))
    assert any("between" in e for e in validate_integration_config(
        "qradar", {"syslog_host": "h", "syslog_port": 999999}))
    assert validate_integration_config("qradar", {"syslog_host": "h", "syslog_port": 514}) == []


def test_unknown_type():
    assert validate_integration_config("carrier-pigeon", {}) == ["Unknown integration type: carrier-pigeon"]


@pytest.mark.asyncio
async def test_create_integration_rejects_invalid_config():
    from src import auth
    from src.main import app

    app.dependency_overrides[auth.get_current_user] = lambda: auth.CurrentUser(
        sub="auth0|t", org_id=uuid.uuid4(), email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/integrations", json={
                "integration_type": "pagerduty",
                "name": "PD",
                "config": {},  # missing routing_key
                "trigger_events": ["test_failed"],
            })
    finally:
        app.dependency_overrides.pop(auth.get_current_user, None)
    assert resp.status_code == 400
    assert "routing_key" in resp.json()["detail"]
