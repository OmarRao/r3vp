# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Integration tests: the executive scorecard now reflects real DB state.

Guards that the CISO scorecard and board PDF are computed from live workloads,
test runs, and threats - not the static mock the endpoints previously returned.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth import CurrentUser, get_current_user
from src.db.session import get_db
from src.main import app
from src.models.appliance import Appliance, Org
from src.models.test_run import TestRun
from src.models.threat_scan import ThreatFinding, ThreatScan
from src.models.workload import Workload
from src.services.executive_snapshot import build_live_scorecard

pytestmark = pytest.mark.integration


async def _seed_small(db_session) -> uuid.UUID:
    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="Acme Recovery Co"))
    db_session.add(Appliance(id=appliance_id, org_id=org_id, name="ap-1",
                             mtls_thumbprint="t", status="active"))
    await db_session.commit()

    now = datetime.now(UTC)
    # 3 workloads: one passing (RTO ok), one failing, one protected-never-tested.
    wl_pass = Workload(appliance_id=appliance_id, name="wl-pass", platform="vmware",
                       provider="vmware", is_protected=True, rto_target_mins=60, rpo_target_mins=60)
    wl_fail = Workload(appliance_id=appliance_id, name="wl-fail", platform="hyperv",
                       provider="hyperv", is_protected=True, rto_target_mins=60, rpo_target_mins=60)
    wl_new = Workload(appliance_id=appliance_id, name="wl-untested", platform="vmware",
                      provider="vmware", is_protected=True, rto_target_mins=60, rpo_target_mins=60)
    db_session.add_all([wl_pass, wl_fail, wl_new])
    await db_session.commit()

    db_session.add(TestRun(workload_id=wl_pass.id, status="passed", started_at=now,
                           completed_at=now, rto_actual_mins=30, rpo_actual_mins=20))
    db_session.add(TestRun(workload_id=wl_fail.id, status="failed", started_at=now,
                           completed_at=now))
    await db_session.commit()

    scan = ThreatScan(org_id=org_id, appliance_id=appliance_id, scan_id="s-1",
                      started_at=now - timedelta(minutes=10), completed_at=now, critical_count=1)
    db_session.add(scan)
    await db_session.commit()
    db_session.add(ThreatFinding(scan_id=scan.id, org_id=org_id, signature_id="Y-1",
                                 threat_name="LockBit", threat_type="ransomware", severity="critical",
                                 host="wl-fail", indicator_type="file", indicator_value="/x",
                                 status="active", detected_at=now))
    await db_session.commit()
    return org_id


@pytest.mark.asyncio
async def test_build_live_scorecard_reflects_db(db_engine, db_session):
    org_id = await _seed_small(db_session)
    snapshot, trend, org_name = await build_live_scorecard(db_session, org_id)

    assert org_name == "Acme Recovery Co"
    assert snapshot["workloads_total"] == 3
    assert snapshot["workloads_tested"] == 2      # pass + fail; untested excluded
    assert snapshot["workloads_passing"] == 1
    assert snapshot["rto_compliance_pct"] == 100  # the single passed run met RTO
    assert snapshot["active_threats"] == 1
    assert snapshot["provider_breakdown"]["vmware"]["total"] == 2
    assert snapshot["provider_breakdown"]["hyperv"]["pass_rate"] == 0
    # The protected-never-tested workload surfaces as a high risk.
    assert any(r["severity"] == "high" and r["workload"] == "wl-untested"
               for r in snapshot["top_risks"])
    assert len(trend) == 12


@pytest.mark.asyncio
async def test_scorecard_endpoint_is_not_mocked(db_engine, db_session):
    org_id = await _seed_small(db_session)

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|test", org_id=org_id, email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/executive/scorecard")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    # The old mock reported 47 total workloads; live data has exactly 3.
    assert data["workloads_total"] == 3
    assert data["workloads_passing"] == 1
    assert data["active_threats"] == 1


@pytest.mark.asyncio
async def test_scorecard_pdf_endpoint_returns_pdf(db_engine, db_session):
    """Renders via weasyprint (native libs present in CI / the API image)."""
    org_id = await _seed_small(db_session)

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|test", org_id=org_id, email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/executive/scorecard/pdf?period=current")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert "X-SHA256" in resp.headers
