"""Continuous validation check engine."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# Checks that require live appliance/Veeam/vCenter telemetry the SaaS side does
# not hold; they are reported "skipped" until the appliance submits results.
LIVE_ONLY_CHECKS = frozenset({"mount_check", "veeam_job_status", "vcenter_connectivity"})

MICRO_CHECKS = {
    "restore_point_freshness": {
        "name": "Restore Point Freshness",
        "description": "Verifies the latest restore point is within the configured RPO window",
        "category": "Data Protection",
    },
    "mount_check": {
        "name": "Mount Endpoint Reachability",
        "description": "Tests that the recovery mount endpoint responds within 5 seconds",
        "category": "Connectivity",
    },
    "veeam_job_status": {
        "name": "Veeam Job Status",
        "description": "Checks the last Veeam backup job completed with Success or Warning status",
        "category": "Backup Health",
    },
    "agent_heartbeat": {
        "name": "Appliance Heartbeat",
        "description": "Confirms the R3VP appliance for this workload reported a heartbeat within the last interval",
        "category": "Appliance Health",
    },
    "vcenter_connectivity": {
        "name": "vCenter Connectivity",
        "description": "Verifies the appliance can reach vCenter and enumerate the protected VM",
        "category": "Connectivity",
    },
    "rpo_compliance": {
        "name": "RPO Compliance Check",
        "description": "Calculates current RPO exposure from last restore point age vs the workload RPO target",
        "category": "SLA Compliance",
    },
}


def _age_mins(ts: datetime | None, now: datetime) -> float | None:
    if ts is None:
        return None
    return (now - ts).total_seconds() / 60.0


def check_restore_point_freshness(
    last_backup_at: datetime | None, rpo_target_mins: int | None, now: datetime | None = None
) -> dict[str, Any]:
    """Latest restore point recency vs the RPO window."""
    now = now or datetime.now(UTC)
    target = rpo_target_mins or 1440  # default 24h if unset
    age = _age_mins(last_backup_at, now)
    if age is None:
        return {"status": "fail", "detail": "No restore point recorded"}
    hours = round(age / 60, 1)
    if age <= target:
        status = "pass"
    elif age <= target * 2:
        status = "warn"
    else:
        status = "fail"
    return {"status": status, "detail": f"Latest restore point {hours}h old (RPO {target}m)",
            "value_hours": hours}


def check_rpo_compliance(
    last_backup_at: datetime | None, rpo_target_mins: int | None, now: datetime | None = None
) -> dict[str, Any]:
    """Strict RPO SLA exposure: current data-loss window vs target."""
    now = now or datetime.now(UTC)
    target = rpo_target_mins or 1440
    age = _age_mins(last_backup_at, now)
    if age is None:
        return {"status": "fail", "detail": "No restore point to measure RPO exposure"}
    exposure = round(age)
    status = "pass" if age <= target else ("warn" if age <= target * 1.5 else "fail")
    return {"status": status, "detail": f"RPO exposure {exposure}m vs target {target}m"}


def check_agent_heartbeat(
    last_heartbeat: datetime | None, interval_mins: int, now: datetime | None = None
) -> dict[str, Any]:
    """Appliance heartbeat recency vs the policy check interval."""
    now = now or datetime.now(UTC)
    age = _age_mins(last_heartbeat, now)
    if age is None:
        return {"status": "fail", "detail": "No heartbeat recorded for the appliance"}
    mins = round(age)
    # Allow one missed interval as a grace window before warning.
    if age <= interval_mins * 2:
        status = "pass"
    elif age <= interval_mins * 4:
        status = "warn"
    else:
        status = "fail"
    return {"status": status, "detail": f"Last heartbeat {mins}m ago (interval {interval_mins}m)"}


def build_check_results(
    checks_enabled: dict[str, bool],
    last_backup_at: datetime | None,
    rpo_target_mins: int | None,
    appliance_last_heartbeat: datetime | None,
    interval_mins: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run every enabled check for one workload and return the per-check results.

    Live-only checks (mount/veeam/vcenter) are reported "skipped" because the
    SaaS side has no live telemetry for them.
    """
    now = now or datetime.now(UTC)
    results: dict[str, Any] = {}
    for check, on in checks_enabled.items():
        if not on:
            continue
        if check == "restore_point_freshness":
            results[check] = check_restore_point_freshness(last_backup_at, rpo_target_mins, now)
        elif check == "rpo_compliance":
            results[check] = check_rpo_compliance(last_backup_at, rpo_target_mins, now)
        elif check == "agent_heartbeat":
            results[check] = check_agent_heartbeat(appliance_last_heartbeat, interval_mins, now)
        elif check in LIVE_ONLY_CHECKS:
            results[check] = {"status": "skipped", "detail": "Requires appliance telemetry"}
        else:
            results[check] = {"status": "skipped", "detail": "Unknown check"}
    return results


def evaluate_check_results(check_results: dict[str, Any]) -> str:
    """Return overall status: pass | warn | fail. Skipped checks are ignored."""
    statuses = [v.get("status", "skip") for v in check_results.values()]
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def compute_continuous_health(recent_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute rolling health from the last N micro-validation runs."""
    if not recent_runs:
        return {"status": "no_data", "pass_rate": 0, "last_check": None, "consecutive_failures": 0}
    total = len(recent_runs)
    passed = sum(1 for r in recent_runs if r.get("status") == "pass")
    pass_rate = round(passed / total * 100)
    consecutive_failures = 0
    for run in reversed(recent_runs):
        if run.get("status") != "pass":
            consecutive_failures += 1
        else:
            break
    last_check = recent_runs[-1].get("ran_at") if recent_runs else None
    overall = "healthy" if pass_rate >= 90 else ("degraded" if pass_rate >= 70 else "failing")
    return {
        "status": overall,
        "pass_rate": pass_rate,
        "last_check": last_check,
        "consecutive_failures": consecutive_failures,
        "total_runs": total,
        "passed": passed,
    }
