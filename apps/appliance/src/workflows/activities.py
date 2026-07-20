"""Temporal activity implementations for the recovery test workflow."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog
from temporalio import activity

from src.config import settings
from src.connectors.vcenter.client import VCenterClient
from src.connectors.veeam.client import VeeamClient
from src.relay.client import RelayClient

log = structlog.get_logger()


# ── Input dataclasses ─────────────────────────────────────────────────────────

@dataclass
class SyncInventoryInput:
    run_id: str

@dataclass
class SelectRestorePointInput:
    run_id: str
    veeam_object_id: str
    rpo_target_mins: int

@dataclass
class RestorePointSelection:
    restore_point_id: str
    creation_time: str  # ISO-8601, used later for RPO measurement

@dataclass
class RecordRtoRpoInput:
    run_id: str
    rpo_creation_iso: str | None
    recovery_start_iso: str | None
    boot_ready_iso: str | None
    rto_target_mins: int
    rpo_target_mins: int
    health_passed: bool

@dataclass
class ProvisionNetworkInput:
    run_id: str

@dataclass
class StartRecoveryInput:
    run_id: str
    restore_point_id: str
    isolated_network: str

@dataclass
class WaitForBootInput:
    run_id: str
    recovery_session_id: str

@dataclass
class RunHealthChecksInput:
    run_id: str
    vm_moref: str

@dataclass
class CaptureEvidenceInput:
    run_id: str
    vm_moref: str | None
    health_results: list[dict] = field(default_factory=list)

@dataclass
class ReportResultInput:
    run_id: str
    passed: bool
    rto_actual_mins: int
    rpo_actual_mins: int
    readiness_score: int
    failure_reason: str | None = None

@dataclass
class TeardownInput:
    run_id: str
    recovery_session_id: str | None
    isolated_network: str | None


# ── Activities ────────────────────────────────────────────────────────────────

@activity.defn
async def sync_inventory(inp: SyncInventoryInput) -> None:
    async with VeeamClient() as veeam:
        vms = await veeam.list_protected_vms()
    relay = RelayClient()
    await relay.sync_inventory({
        "run_id": inp.run_id,
        "vms": [
            {
                "object_id": vm.object_id,
                "name": vm.name,
                "platform": vm.platform,
                "os_type": None,
                "is_protected": True,
                "last_backup": vm.last_backup.isoformat() if vm.last_backup else None,
                "moref": None,
            }
            for vm in vms
        ],
    })
    await relay.close()


@activity.defn
async def select_restore_point(inp: SelectRestorePointInput) -> RestorePointSelection:
    """Return the latest consistent restore point within the RPO window."""
    from src.connectors.veeam import rest
    async with VeeamClient() as veeam:
        points = await veeam.list_restore_points(inp.veeam_object_id)
    best = rest.select_restore_point(
        points, datetime.now(UTC), rpo_target_mins=inp.rpo_target_mins
    )
    age_mins = rest.compute_rpo_minutes(best.creationTime, datetime.now(UTC))
    log.info("restore point selected", id=best.id, age_mins=age_mins)
    return RestorePointSelection(
        restore_point_id=best.id,
        creation_time=best.creationTime.isoformat(),
    )


@activity.defn
async def provision_isolated_network(inp: ProvisionNetworkInput) -> str:
    network_name = f"{settings.isolated_network_name}-{inp.run_id[:8]}"
    with VCenterClient() as vc:
        if settings.vcenter_network_backend.lower() == "dvs":
            vc.create_isolated_portgroup_dvs(
                dvs_name=settings.vcenter_dvs_name,
                vlan_id=settings.isolated_vlan_id,
                name=network_name,
            )
        else:
            vc.create_isolated_portgroup(
                vswitch_name=settings.vcenter_vswitch_name,
                vlan_id=settings.isolated_vlan_id,
                name=network_name,
            )
    return network_name


@activity.defn
async def start_instant_recovery(inp: StartRecoveryInput) -> str:
    async with VeeamClient() as veeam:
        session_id = await veeam.start_instant_recovery(
            restore_point_id=inp.restore_point_id,
            target_datastore="",  # resolved by Veeam automatically
            isolated_network=inp.isolated_network,
        )
    log.info("instant recovery started", session_id=session_id)
    return session_id


@activity.defn
async def wait_for_vm_boot(inp: WaitForBootInput) -> str:
    """Poll the Veeam instant-recovery session until the recovered VM is published,
    then resolve its real vCenter moref from the session's restored-object reference.

    Falls back to a deterministic ``recovered-{session_id}`` placeholder only when
    the moref cannot be resolved (e.g. the live session response shape has not yet
    been confirmed against a real Veeam server). See the real-lab verification
    boundary in ADR-003 / the PR: the restored-object key names in
    ``vcenter/moref.py::parse_recovered_vm_identity`` must be confirmed against a
    recorded live session before the placeholder path can be removed.
    """
    import asyncio

    from src.connectors.vcenter.client import VCenterClient
    from src.connectors.vcenter.moref import parse_recovered_vm_identity
    from src.connectors.veeam import rest
    from src.connectors.veeam.rest import PollDecision
    from src.connectors.veeam.session_states import VeeamSessionState

    state = VeeamSessionState.UNKNOWN.value
    session_body: dict = {}
    max_polls = max(
        1, settings.recovery_poll_timeout_secs // max(1, settings.recovery_poll_interval_secs)
    )
    async with VeeamClient() as veeam:
        for _ in range(max_polls):
            session_body = await veeam.get_session(inp.recovery_session_id)
            state = rest.parse_session_state(session_body)
            decision = rest.classify_poll(state)
            if decision == PollDecision.PUBLISHED:
                break
            if decision == PollDecision.FAILED:
                raise RuntimeError(
                    f"Veeam instant recovery session failed (state: {state})"
                )
            await asyncio.sleep(settings.recovery_poll_interval_secs)
        else:
            raise RuntimeError(
                "Veeam instant recovery session never became published "
                f"(last state: {state})"
            )

    identity = parse_recovered_vm_identity(session_body)
    if identity.lookup_plan():
        with VCenterClient() as vc:
            moref = vc.resolve_moref(identity)
        if moref:
            return moref
        log.warning(
            "recovered moref not resolved; using placeholder",
            session_id=inp.recovery_session_id,
        )
    return f"recovered-{inp.recovery_session_id}"


@activity.defn
async def run_health_checks(inp: RunHealthChecksInput) -> list[dict]:
    from src.health_checks.linux_os import LinuxOSHealthCheck
    from src.health_checks.windows_os import WindowsOSHealthCheck
    checks = [WindowsOSHealthCheck(), LinuxOSHealthCheck()]
    results = []
    for check in checks:
        result = await check.run(inp.vm_moref)
        results.append(result)
        relay = RelayClient()
        await relay.post_progress(inp.run_id, {"step": check.name, **result})
        await relay.close()
    return results


@activity.defn
async def capture_evidence(inp: CaptureEvidenceInput) -> None:
    if not inp.vm_moref:
        return
    relay = RelayClient()
    with VCenterClient() as vc:
        screenshot = vc.take_screenshot(inp.vm_moref)
        if screenshot:
            await relay.upload_evidence(inp.run_id, "screenshot.png", screenshot)
    await relay.close()


@activity.defn
async def record_rto_rpo(inp: RecordRtoRpoInput) -> dict:
    """Compute real RTO/RPO minutes and a readiness score from workflow timestamps.

    RTO = interval from starting instant recovery to the guest becoming boot-ready.
    RPO = age of the recovered restore point at validation time.
    Timestamps are supplied by the workflow (Temporal ``workflow.now()``), keeping
    this activity deterministic and unit-testable via the pure helpers in
    ``connectors.veeam.rest``.
    """
    from src.connectors.veeam import rest

    def _parse(iso: str | None) -> datetime | None:
        return datetime.fromisoformat(iso) if iso else None

    now = datetime.now(UTC)
    rpo_creation = _parse(inp.rpo_creation_iso)
    recovery_start = _parse(inp.recovery_start_iso)
    boot_ready = _parse(inp.boot_ready_iso)

    rpo_actual = rest.compute_rpo_minutes(rpo_creation, now) if rpo_creation else 0
    if recovery_start and boot_ready:
        rto_actual = rest.compute_rto_minutes(recovery_start, boot_ready)
    else:
        rto_actual = 0
    score = rest.readiness_score(
        health_passed=inp.health_passed,
        rto_actual_mins=rto_actual,
        rto_target_mins=inp.rto_target_mins,
        rpo_actual_mins=rpo_actual,
        rpo_target_mins=inp.rpo_target_mins,
    )
    return {
        "rto_actual_mins": rto_actual,
        "rpo_actual_mins": rpo_actual,
        "readiness_score": score,
    }


@activity.defn
async def report_results(inp: ReportResultInput) -> None:
    relay = RelayClient()
    await relay.post_result(inp.run_id, {
        "passed": inp.passed,
        "rto_actual_mins": inp.rto_actual_mins,
        "rpo_actual_mins": inp.rpo_actual_mins,
        "readiness_score": inp.readiness_score,
        "failure_reason": inp.failure_reason,
    })
    await relay.close()


@activity.defn
async def detect_provider_vms(inp: SyncInventoryInput) -> list[dict]:
    """
    Detect VMs and workloads from the configured provider.

    Routes to the correct connector based on settings.provider.
    Returns a list of VM dicts in the standard format for relay sync.
    """
    from src.config import settings as _s

    provider = _s.provider.lower()

    if provider == "hyperv":
        from src.connectors.hyperv.client import HyperVClient
        client = HyperVClient(host=_s.hyperv_host)
        if not client.connect():
            return []
        vms = client.list_vms()
        return [
            {
                "object_id": vm.vm_id,
                "name": vm.name,
                "platform": "hyperv",
                "os_type": "windows",
                "is_protected": True,
                "moref": vm.vm_id,
            }
            for vm in vms
        ]

    elif provider == "aws":
        from src.connectors.aws_backup.client import AWSBackupClient
        client = AWSBackupClient(region=_s.aws_region)
        if not client.connect():
            return []
        vaults = client.list_vaults()
        result = []
        for vault in vaults:
            rps = client.list_recovery_points(vault.vault_name)
            seen: set[str] = set()
            for rp in rps:
                resource_id = rp.resource_arn.split("/")[-1]
                if resource_id not in seen:
                    seen.add(resource_id)
                    result.append({
                        "object_id": rp.resource_arn,
                        "name": resource_id,
                        "platform": "aws",
                        "os_type": None,
                        "is_protected": True,
                        "moref": rp.resource_arn,
                        "last_backup": rp.creation_date.isoformat() if rp.creation_date else None,
                    })
        return result

    elif provider == "azure":
        from src.connectors.azure_backup.client import AzureBackupClient
        client = AzureBackupClient(
            subscription_id=_s.azure_subscription_id,
            tenant_id=_s.azure_tenant_id,
        )
        if not client.connect():
            return []
        items = client.list_protected_vms(
            vault_name=_s.azure_vault_name,
            resource_group=_s.azure_resource_group,
        )
        return [
            {
                "object_id": item.item_id,
                "name": item.friendly_name,
                "platform": "azure",
                "os_type": None,
                "is_protected": True,
                "moref": item.item_id,
                "last_backup": item.last_backup_time.isoformat() if item.last_backup_time else None,
            }
            for item in items
        ]

    elif provider == "proxmox":
        import asyncio

        from src.connectors.proxmox.client import ProxmoxClient
        client = ProxmoxClient()
        if await asyncio.to_thread(client.connect):
            vms = await asyncio.to_thread(client.list_vms)
            return [{"name": v.name, "provider": "proxmox", "status": v.status} for v in vms]

    elif provider == "nutanix":
        from src.connectors.nutanix.client import NutanixClient
        client = NutanixClient()
        if await client.connect():
            vms = await client.list_vms()
            return [{"name": v.name, "provider": "nutanix", "status": v.power_state} for v in vms]

    elif provider == "rhv":
        import asyncio

        from src.connectors.rhv.client import RHVClient
        client = RHVClient()
        if await asyncio.to_thread(client.connect):
            vms = await asyncio.to_thread(client.list_vms)
            return [{"name": v.name, "provider": "rhv", "status": v.status} for v in vms]

    elif provider == "xenserver":
        import asyncio

        from src.connectors.xenserver.client import XenServerClient
        client = XenServerClient()
        if await asyncio.to_thread(client.connect):
            vms = await asyncio.to_thread(client.list_vms)
            return [{"name": v.name_label, "provider": "xenserver", "status": v.power_state} for v in vms]

    elif provider == "sangfor":
        from src.connectors.sangfor.client import SangforClient
        client = SangforClient()
        if await client.connect():
            vms = await client.list_vms()
            return [{"name": v.name, "provider": "sangfor", "status": v.status} for v in vms]

    elif provider == "gcp":
        import asyncio

        from src.connectors.gcp_backup.client import GCPBackupClient
        client = GCPBackupClient()
        if await asyncio.to_thread(client.connect):
            instances = await asyncio.to_thread(client.list_instances)
            return [{"name": i.name, "provider": "gcp", "status": i.status} for i in instances]

    else:
        # Default: vmware -- existing behavior is handled by the existing sync_inventory activity
        pass

    return []


@activity.defn
async def teardown_isolated_env(inp: TeardownInput) -> None:
    if inp.recovery_session_id:
        async with VeeamClient() as veeam:
            await veeam.stop_instant_recovery(inp.recovery_session_id)
    if inp.isolated_network:
        with VCenterClient() as vc:
            vc.remove_portgroup("", inp.isolated_network)
    log.info("isolated environment torn down", run_id=inp.run_id)
