"""Onboarding wizard step definitions and progress logic."""
from __future__ import annotations

from typing import Any

STEPS = [
    {
        "step": 1,
        "id": "org_profile",
        "title": "Organization Profile",
        "description": "Set your organization name, industry, and recovery objectives",
        "required_fields": ["org_name", "industry", "default_rto_target_mins", "default_rpo_target_mins"],
    },
    {
        "step": 2,
        "id": "deploy_appliance",
        "title": "Deploy Appliance",
        "description": "Download and deploy the R3VP appliance inside your environment",
        "required_fields": [],
        "instructions": {
            "docker": "docker run -d --name r3vp-appliance -e R3VP_TOKEN=<token> -e R3VP_API_URL=https://api.r3vp.io r3vp/appliance:latest",
            "ova": "Download the OVA from the portal, deploy to vSphere, and set the R3VP_TOKEN OVF property",
            "token_hint": "Your registration token is shown below. It expires in 24 hours.",
        },
    },
    {
        "step": 3,
        "id": "connect_veeam",
        "title": "Connect Veeam B&R",
        "description": "Enter your Veeam Backup and Replication server details",
        "required_fields": ["veeam_host", "veeam_port", "veeam_username"],
        "notes": "Credentials are encrypted with SOPS + age and never leave your environment",
    },
    {
        "step": 4,
        "id": "discover_workloads",
        "title": "Discover Workloads",
        "description": "Sync your protected VM inventory from Veeam and vCenter",
        "required_fields": [],
        "action": "sync_inventory",
    },
    {
        "step": 5,
        "id": "first_test",
        "title": "Run First Validation",
        "description": "Select a workload and run your first automated recovery test",
        "required_fields": ["workload_id"],
        "action": "trigger_test_run",
    },
    {
        "step": 6,
        "id": "complete",
        "title": "Setup Complete",
        "description": "Your R3VP environment is ready",
        "required_fields": [],
    },
]


def get_step_definition(step: int) -> dict[str, Any] | None:
    return next((s for s in STEPS if s["step"] == step), None)


def is_step_complete(step_id: str, step_data: dict[str, Any]) -> bool:
    if step_id == "org_profile":
        return bool(step_data.get("org_name"))
    if step_id == "deploy_appliance":
        return bool(step_data.get("appliance_id"))
    if step_id == "connect_veeam":
        return bool(step_data.get("veeam_connected"))
    if step_id == "discover_workloads":
        return (step_data.get("workload_count", 0) or 0) > 0
    if step_id == "first_test":
        return bool(step_data.get("first_test_run_id"))
    return step_id == "complete"


def compute_progress(session_step_data: dict[str, Any]) -> dict[str, Any]:
    completed_steps = []
    for step_def in STEPS:
        if is_step_complete(step_def["id"], session_step_data):
            completed_steps.append(step_def["step"])
    pct = round(len(completed_steps) / len(STEPS) * 100)
    return {"completed_steps": completed_steps, "total_steps": len(STEPS), "percent": pct}
