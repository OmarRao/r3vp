"""Unit tests for the appliance router — no DB required (service layer mocked)."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

APPLIANCE_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_register_returns_registered() -> None:
    with patch("src.routers.appliances.svc.register_appliance", new_callable=AsyncMock) as mock_reg:
        mock_reg.return_value = None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/v1/appliance/register",
                json={
                    "appliance_id": APPLIANCE_ID,
                    "org_id": ORG_ID,
                    "name": "test-appliance",
                    "version": "0.1.0",
                    "mtls_thumbprint": "AABBCC",
                },
                headers={"X-Appliance-ID": APPLIANCE_ID, "X-Org-ID": ORG_ID},
            )
    assert resp.status_code == 200
    assert resp.json()["status"] == "registered"
