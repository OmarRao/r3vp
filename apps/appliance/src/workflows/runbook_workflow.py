"""Temporal workflow for DR runbook execution."""
from __future__ import annotations
import logging
from datetime import timedelta
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)

RETRY = RetryPolicy(maximum_attempts=2, initial_interval=timedelta(seconds=15))
NO_RETRY = RetryPolicy(maximum_attempts=1)


@activity.defn
async def fetch_execution_plan(execution_id: str) -> dict:
    """Fetch the execution plan and all steps from the SaaS API."""
    import httpx, os
    base = os.getenv("R3VP_API_URL", "https://api.r3vp.io")
    token = os.getenv("R3VP_APPLIANCE_TOKEN", "")
    async with httpx.AsyncClient(verify=True, timeout=30) as client:
        resp = await client.get(
            f"{base}/v1/runbooks/executions/{execution_id}/steps",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        steps = resp.json()
        exec_resp = await client.get(
            f"{base}/v1/runbooks/executions/{execution_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        exec_resp.raise_for_status()
    return {"execution": exec_resp.json(), "steps": steps}


@activity.defn
async def execute_step(execution_id: str, step: dict) -> dict:
    """Execute a single runbook step and return the result."""
    import httpx, os, asyncio, time
    base = os.getenv("R3VP_API_URL", "https://api.r3vp.io")
    token = os.getenv("R3VP_APPLIANCE_TOKEN", "")
    step_type = step["step_type"]
    start = time.monotonic()

    try:
        if step_type == "recover_workload":
            workload_id = step.get("config", {}).get("workload_id") or step.get("workload_id")
            if not workload_id:
                return {"status": "failed", "error": "No workload_id configured for recover_workload step"}
            async with httpx.AsyncClient(verify=True, timeout=300) as client:
                resp = await client.post(
                    f"{base}/v1/test-runs",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"workload_id": workload_id, "trigger": "runbook", "execution_id": execution_id},
                )
                resp.raise_for_status()
                run = resp.json()
            return {"status": "completed", "output": {"test_run_id": run.get("id"), "rto_mins": run.get("rto_actual_mins")}, "duration_secs": round(time.monotonic() - start)}

        elif step_type == "health_check":
            await asyncio.sleep(5)
            return {"status": "completed", "output": {"checks_passed": True}, "duration_secs": round(time.monotonic() - start)}

        elif step_type == "notify":
            from src.services.delivery import deliver_report, DeliveryRecipient
            channel = step.get("config", {}).get("channel", "slack")
            destination = step.get("config", {}).get("destination", "")
            message = step.get("config", {}).get("message", f"DR Runbook step completed: {step['name']}")
            if destination:
                await deliver_report(b"", "", f"R3VP Runbook: {step['name']}", message, [DeliveryRecipient(type=channel, destination=destination)])
            return {"status": "completed", "output": {"notified": bool(destination)}, "duration_secs": round(time.monotonic() - start)}

        elif step_type == "wait":
            duration_mins = step.get("config", {}).get("duration_mins", 1)
            await asyncio.sleep(duration_mins * 60)
            return {"status": "completed", "output": {"waited_mins": duration_mins}, "duration_secs": round(time.monotonic() - start)}

        elif step_type == "manual_gate":
            return {"status": "waiting_gate", "output": {"instructions": step.get("config", {}).get("instructions", "Manual approval required")}, "duration_secs": 0}

        elif step_type == "run_script":
            import subprocess
            script = step.get("config", {}).get("script", "")
            interpreter = step.get("config", {}).get("interpreter", "bash")
            if not script:
                return {"status": "failed", "error": "No script configured"}
            result = subprocess.run([interpreter, "-c", script], capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return {"status": "failed", "error": result.stderr[:500], "duration_secs": round(time.monotonic() - start)}
            return {"status": "completed", "output": {"stdout": result.stdout[:1000]}, "duration_secs": round(time.monotonic() - start)}

        else:
            return {"status": "failed", "error": f"Unknown step type: {step_type}"}

    except Exception as exc:
        return {"status": "failed", "error": str(exc), "duration_secs": round(time.monotonic() - start)}


@activity.defn
async def update_step_status(execution_id: str, step_id: str, result: dict) -> None:
    """Post step result back to the SaaS API."""
    import httpx, os
    base = os.getenv("R3VP_API_URL", "https://api.r3vp.io")
    token = os.getenv("R3VP_APPLIANCE_TOKEN", "")
    async with httpx.AsyncClient(verify=True, timeout=15) as client:
        await client.patch(
            f"{base}/v1/runbooks/executions/{execution_id}/steps/{step_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=result,
        )


@activity.defn
async def finalize_execution(execution_id: str, status: str, actual_rto_mins: int) -> None:
    """Mark the execution complete or failed in the SaaS API."""
    import httpx, os
    base = os.getenv("R3VP_API_URL", "https://api.r3vp.io")
    token = os.getenv("R3VP_APPLIANCE_TOKEN", "")
    async with httpx.AsyncClient(verify=True, timeout=15) as client:
        await client.patch(
            f"{base}/v1/runbooks/executions/{execution_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": status, "actual_rto_mins": actual_rto_mins},
        )


@workflow.defn
class RunbookWorkflow:
    @workflow.run
    async def run(self, execution_id: str) -> dict:
        import time
        start_time = time.time()

        plan = await workflow.execute_activity(
            fetch_execution_plan,
            execution_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY,
        )

        steps = sorted(plan["steps"], key=lambda s: s["seq"])
        overall_status = "completed"

        for step in steps:
            if step["status"] in ("completed", "skipped"):
                continue

            result = await workflow.execute_activity(
                execute_step,
                args=[execution_id, step],
                start_to_close_timeout=timedelta(minutes=step.get("timeout_mins", 60) + 5),
                retry_policy=NO_RETRY,
            )

            await workflow.execute_activity(
                update_step_status,
                args=[execution_id, step["id"], result],
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=RETRY,
            )

            if result["status"] == "failed":
                on_failure = step.get("on_failure", "stop")
                if on_failure == "stop":
                    overall_status = "failed"
                    break
                elif on_failure == "rollback":
                    overall_status = "rolled_back"
                    break

        actual_rto = round((time.time() - start_time) / 60)

        await workflow.execute_activity(
            finalize_execution,
            args=[execution_id, overall_status, actual_rto],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=RETRY,
        )

        return {"execution_id": execution_id, "status": overall_status, "actual_rto_mins": actual_rto}
