"""Main recovery validation workflow.

Orchestrated by Temporal — each Activity is independently retried,
and TeardownIsolatedEnv runs as a saga compensation step (always executes).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from src.workflows.activities import (
    SyncInventoryInput,
    SelectRestorePointInput,
    ProvisionNetworkInput,
    StartRecoveryInput,
    WaitForBootInput,
    RunHealthChecksInput,
    CaptureEvidenceInput,
    TeardownInput,
    ReportResultInput,
    sync_inventory,
    select_restore_point,
    provision_isolated_network,
    start_instant_recovery,
    wait_for_vm_boot,
    run_health_checks,
    capture_evidence,
    record_rto_rpo,
    report_results,
    teardown_isolated_env,
)


@dataclass
class RecoveryTestInput:
    run_id: str
    workload_id: str
    veeam_object_id: str
    vcenter_moref: str
    rto_target_mins: int
    rpo_target_mins: int


@dataclass
class RecoveryTestResult:
    run_id: str
    passed: bool
    rto_actual_mins: int
    rpo_actual_mins: int
    readiness_score: int
    failure_reason: str | None = None


_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
)

_SHORT_TIMEOUT = timedelta(minutes=10)
_BOOT_TIMEOUT = timedelta(minutes=30)


@workflow.defn
class RecoveryTestWorkflow:
    @workflow.run
    async def run(self, inp: RecoveryTestInput) -> RecoveryTestResult:
        isolated_network: str | None = None
        recovery_session_id: str | None = None
        recovered_vm_moref: str | None = None
        start_time = workflow.now()
        passed = False
        failure_reason: str | None = None
        health_results: list[dict] = []

        try:
            # 1. Discover and sync inventory
            await workflow.execute_activity(
                sync_inventory,
                SyncInventoryInput(run_id=inp.run_id),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            # 2. Select the best (latest consistent) restore point
            restore_point = await workflow.execute_activity(
                select_restore_point,
                SelectRestorePointInput(
                    run_id=inp.run_id,
                    veeam_object_id=inp.veeam_object_id,
                    rpo_target_mins=inp.rpo_target_mins,
                ),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            # 3. Provision isolated VLAN (no blast radius to production)
            isolated_network = await workflow.execute_activity(
                provision_isolated_network,
                ProvisionNetworkInput(run_id=inp.run_id),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            # 4. Start Veeam Instant Recovery into isolated network
            recovery_session_id = await workflow.execute_activity(
                start_instant_recovery,
                StartRecoveryInput(
                    run_id=inp.run_id,
                    restore_point_id=restore_point,
                    isolated_network=isolated_network,
                ),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            # 5. Wait for the VM to boot and VMware Tools to become available
            recovered_vm_moref = await workflow.execute_activity(
                wait_for_vm_boot,
                WaitForBootInput(run_id=inp.run_id, recovery_session_id=recovery_session_id),
                start_to_close_timeout=_BOOT_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            # 6. Run OS + application health checks
            health_results = await workflow.execute_activity(
                run_health_checks,
                RunHealthChecksInput(
                    run_id=inp.run_id,
                    vm_moref=recovered_vm_moref,
                ),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            passed = all(r["passed"] for r in health_results)

        except Exception as exc:
            failure_reason = str(exc)
            workflow.logger.error("recovery test failed", error=str(exc))

        finally:
            # 7. Capture evidence regardless of outcome
            await workflow.execute_activity(
                capture_evidence,
                CaptureEvidenceInput(
                    run_id=inp.run_id,
                    vm_moref=recovered_vm_moref,
                    health_results=health_results,
                ),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            # 8. Measure RTO/RPO
            result = await workflow.execute_activity(
                record_rto_rpo,
                inp,
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            # 9. Report back to SaaS before teardown
            await workflow.execute_activity(
                report_results,
                ReportResultInput(
                    run_id=inp.run_id,
                    passed=passed,
                    rto_actual_mins=result["rto_actual_mins"],
                    rpo_actual_mins=result["rpo_actual_mins"],
                    readiness_score=result["readiness_score"],
                    failure_reason=failure_reason,
                ),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

            # 10. Always tear down — saga compensation
            await workflow.execute_activity(
                teardown_isolated_env,
                TeardownInput(
                    run_id=inp.run_id,
                    recovery_session_id=recovery_session_id,
                    isolated_network=isolated_network,
                ),
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )

        return RecoveryTestResult(
            run_id=inp.run_id,
            passed=passed,
            rto_actual_mins=result["rto_actual_mins"],
            rpo_actual_mins=result["rpo_actual_mins"],
            readiness_score=result["readiness_score"],
            failure_reason=failure_reason,
        )
