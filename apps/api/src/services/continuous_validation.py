"""Continuous validation check engine."""
from __future__ import annotations
from typing import Any

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


def evaluate_check_results(check_results: dict[str, Any]) -> str:
    """Return overall status: pass | warn | fail."""
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
