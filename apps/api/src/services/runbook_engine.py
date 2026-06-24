"""Runbook execution engine: step sequencing and dependency resolution."""
from __future__ import annotations
from typing import Any


def resolve_execution_order(steps: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """
    Topological sort of runbook steps respecting depends_on_seq.
    Returns a list of waves, where each wave is a list of steps
    that can run concurrently (all their dependencies are in prior waves).
    """
    seq_map = {s["seq"]: s for s in steps}
    completed: set[int] = set()
    remaining = list(steps)
    waves: list[list[dict]] = []

    max_iterations = len(steps) + 1
    iteration = 0

    while remaining:
        iteration += 1
        if iteration > max_iterations:
            raise ValueError("Circular dependency detected in runbook steps")

        ready = [
            s for s in remaining
            if all(dep in completed for dep in s.get("depends_on_seq", []))
        ]
        if not ready:
            raise ValueError("No runbook steps are ready: possible circular dependency")

        waves.append(ready)
        for s in ready:
            completed.add(s["seq"])
            remaining.remove(s)

    return waves


def build_execution_plan(runbook: dict, steps: list[dict]) -> dict[str, Any]:
    """Build a structured execution plan for a runbook."""
    waves = resolve_execution_order(steps)
    total_timeout = sum(
        max(s.get("timeout_mins", 60) for s in wave)
        for wave in waves
    )
    return {
        "runbook_id": str(runbook["id"]),
        "runbook_name": runbook["name"],
        "scenario": runbook["scenario"],
        "target_rto_mins": runbook.get("rto_target_mins"),
        "waves": [
            {
                "wave": i + 1,
                "parallel": len(wave) > 1 or any(s.get("parallel") for s in wave),
                "steps": [
                    {
                        "seq": s["seq"],
                        "name": s["name"],
                        "step_type": s["step_type"],
                        "timeout_mins": s.get("timeout_mins", 60),
                        "on_failure": s.get("on_failure", "stop"),
                        "config": s.get("config", {}),
                    }
                    for s in wave
                ],
            }
            for i, wave in enumerate(waves)
        ],
        "estimated_duration_mins": total_timeout,
        "step_count": len(steps),
    }


def compute_rto(started_at_iso: str, completed_at_iso: str) -> int:
    """Compute actual RTO in minutes from ISO timestamps."""
    from datetime import datetime, timezone
    fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
    try:
        start = datetime.fromisoformat(started_at_iso)
        end = datetime.fromisoformat(completed_at_iso)
        return max(0, round((end - start).total_seconds() / 60))
    except Exception:
        return 0
