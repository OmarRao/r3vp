"""Unit tests for ransomware restore-point threat analysis (pure) + the endpoint."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.services.threat_analysis import (
    analyze_restore_points,
    match_ransomware_extensions,
    select_clean_restore_point,
)


def test_match_ransomware_extensions():
    assert match_ransomware_extensions([".locky", "txt", ".WCRY", "docx"]) == ["locky", "wcry"]
    assert match_ransomware_extensions(["pdf", "xlsx"]) == []


def test_entropy_anomaly_flagged_high():
    [res] = analyze_restore_points([{"id": "rp1", "avg_entropy": 7.95, "total_files": 100}])
    assert res["max_severity"] == "high"
    assert res["is_clean"] is False
    assert any(i["type"] == "entropy_anomaly" for i in res["indicators"])


def test_mass_rename_flagged():
    [res] = analyze_restore_points([
        {"id": "rp1", "avg_entropy": 5.0, "total_files": 100, "renamed_files": 40}
    ])
    assert any(i["type"] == "mass_file_rename" for i in res["indicators"])
    assert res["is_clean"] is False


def test_known_extension_is_critical():
    [res] = analyze_restore_points([
        {"id": "rp1", "avg_entropy": 5.0, "total_files": 100, "new_extensions": [".ryuk"]}
    ])
    assert res["max_severity"] == "critical"
    assert res["is_clean"] is False


def test_clean_restore_point_is_the_newest_unflagged():
    rps = [
        {"id": "rp1", "created_at": "2026-06-01", "avg_entropy": 4.5, "total_files": 100},
        {"id": "rp2", "created_at": "2026-06-02", "avg_entropy": 4.6, "total_files": 100},
        # Encrypted-looking latest point should be skipped.
        {"id": "rp3", "created_at": "2026-06-03", "avg_entropy": 7.95, "total_files": 100},
    ]
    clean = select_clean_restore_point(rps)
    assert clean is not None
    assert clean["restore_point_id"] == "rp2"


def test_all_flagged_returns_none():
    rps = [{"id": "rp1", "avg_entropy": 7.99, "total_files": 100, "new_extensions": [".conti"]}]
    assert select_clean_restore_point(rps) is None


def test_entropy_spike_relative_to_baseline():
    rps = [
        {"id": "rp1", "avg_entropy": 4.0, "total_files": 100},
        {"id": "rp2", "avg_entropy": 4.1, "total_files": 100},
        {"id": "rp3", "avg_entropy": 6.0, "total_files": 100},  # jump vs ~4.0 baseline
    ]
    results = analyze_restore_points(rps)
    assert any(i["type"] == "entropy_spike" for i in results[2]["indicators"])


@pytest.mark.asyncio
async def test_analyze_endpoint(monkeypatch):
    from src import auth
    from src.main import app

    app.dependency_overrides[auth.get_current_user] = lambda: auth.CurrentUser(
        sub="auth0|t", org_id=uuid.uuid4(), email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/threat-intel/analyze-restore-points", json=[
                {"id": "rp1", "created_at": "2026-06-01", "avg_entropy": 4.5, "total_files": 100},
                {"id": "rp2", "created_at": "2026-06-02", "avg_entropy": 7.96, "total_files": 100,
                 "new_extensions": [".lockbit"]},
            ])
    finally:
        app.dependency_overrides.pop(auth.get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["flagged_restore_points"] == 1
    assert data["recommended_clean_restore_point"] == "rp1"
    assert data["threats_found"] >= 1


@pytest.mark.asyncio
async def test_analyze_endpoint_forbidden_without_permission():
    """A role with no mapped permissions (empty set) must be rejected with 403."""
    from src import auth
    from src.main import app

    app.dependency_overrides[auth.get_current_user] = lambda: auth.CurrentUser(
        sub="auth0|x", org_id=uuid.uuid4(), email="x@example.com", role="unmapped-role"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/threat-intel/analyze-restore-points", json=[])
    finally:
        app.dependency_overrides.pop(auth.get_current_user, None)
    assert resp.status_code == 403
