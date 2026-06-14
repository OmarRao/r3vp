"""Temporal worker — registers the workflow and all activities."""
from temporalio.client import Client, TLSConfig
from temporalio.worker import Worker

from src.config import settings
from src.workflows.recovery_test import RecoveryTestWorkflow
from src.workflows.activities import (
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


async def run_worker() -> None:
    with open(settings.mtls_cert_path, "rb") as f:
        client_cert = f.read()
    with open(settings.mtls_key_path, "rb") as f:
        client_key = f.read()

    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        tls=TLSConfig(client_cert=client_cert, client_private_key=client_key),
    )

    async with Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[RecoveryTestWorkflow],
        activities=[
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
        ],
    ):
        await client.get_workflow_handle("never")  # blocks forever
