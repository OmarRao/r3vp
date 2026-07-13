"""Unit tests for the continuous-validation micro-check evaluators."""
from datetime import UTC, datetime, timedelta

from src.services.continuous_validation import (
    build_check_results,
    check_agent_heartbeat,
    check_restore_point_freshness,
    check_rpo_compliance,
    evaluate_check_results,
)

NOW = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def test_restore_point_freshness_thresholds():
    assert check_restore_point_freshness(None, 60, NOW)["status"] == "fail"
    assert check_restore_point_freshness(NOW - timedelta(minutes=30), 60, NOW)["status"] == "pass"
    assert check_restore_point_freshness(NOW - timedelta(minutes=90), 60, NOW)["status"] == "warn"
    assert check_restore_point_freshness(NOW - timedelta(minutes=200), 60, NOW)["status"] == "fail"


def test_rpo_compliance_thresholds():
    assert check_rpo_compliance(NOW - timedelta(minutes=30), 60, NOW)["status"] == "pass"
    assert check_rpo_compliance(NOW - timedelta(minutes=80), 60, NOW)["status"] == "warn"
    assert check_rpo_compliance(NOW - timedelta(minutes=120), 60, NOW)["status"] == "fail"
    assert check_rpo_compliance(None, 60, NOW)["status"] == "fail"


def test_agent_heartbeat_thresholds():
    assert check_agent_heartbeat(None, 15, NOW)["status"] == "fail"
    assert check_agent_heartbeat(NOW - timedelta(minutes=10), 15, NOW)["status"] == "pass"
    assert check_agent_heartbeat(NOW - timedelta(minutes=40), 15, NOW)["status"] == "warn"
    assert check_agent_heartbeat(NOW - timedelta(minutes=100), 15, NOW)["status"] == "fail"


def test_build_check_results_skips_live_and_disabled():
    checks = {
        "restore_point_freshness": True,
        "agent_heartbeat": True,
        "mount_check": True,      # live-only -> skipped
        "veeam_job_status": False,  # disabled -> absent
    }
    results = build_check_results(
        checks, NOW - timedelta(minutes=30), 60, NOW - timedelta(minutes=5), 15, NOW
    )
    assert set(results) == {"restore_point_freshness", "agent_heartbeat", "mount_check"}
    assert results["mount_check"]["status"] == "skipped"
    assert "veeam_job_status" not in results


def test_evaluate_ignores_skipped():
    assert evaluate_check_results({
        "a": {"status": "pass"}, "b": {"status": "skipped"},
    }) == "pass"
    assert evaluate_check_results({
        "a": {"status": "pass"}, "b": {"status": "warn"},
    }) == "warn"
    assert evaluate_check_results({
        "a": {"status": "fail"}, "b": {"status": "pass"},
    }) == "fail"
