# ADR-003: Real Veeam B&R + vCenter Recovery-Validation Connector

**Status:** Proposed
**Date:** 2026-07-01
**Deciders:** Omar Rao (Engineer, Data Resilience, Cybersecurity and Privacy)

## Context

The appliance workflow engine (Temporal) and the connector *shells* exist, but the
recovery-test path is stubbed. Specifically:

- `apps/appliance/src/workflows/activities.py::wait_for_vm_boot` returns a placeholder
  moref (`recovered-{session_id}`) instead of resolving the recovered VM from the Veeam
  instant-recovery session.
- Health checks, RTO/RPO measurement, and evidence capture are partially wired but never
  exercised against a live restore.
- `apps/appliance/src/connectors/veeam/client.py` implements auth, discovery, and
  instant-recovery start/stop, but the end-to-end "prove a workload recovers" loop has
  never run against a real Veeam B&R server + vCenter.

This ADR specifies the concrete implementation so it can be built and verified the moment a
Veeam B&R + vCenter lab (or the Veeam API sandbox) is available. It does not change runtime
behavior on its own.

Key constraints (unchanged from ADR-001):
- Customer credentials never leave the customer environment (SOPS + age vault).
- The appliance is outbound-only; it never accepts inbound connections.
- Must support Veeam B&R REST API v1.0 / v1.1 / v1.2 (auto-detected) and vSphere via pyVmomi.

## Decision

Implement a single Temporal workflow, `RecoveryTestWorkflow`, composed of idempotent
activities that drive Veeam Instant Recovery into an isolated vCenter network, validate the
guest, measure RTO/RPO, capture evidence, and always tear down.

### Recovery-test data flow

1. **select_restore_point** (Veeam): resolve the newest clean restore point for the workload
   within the RPO window. RPO = `restore_point.creationTime` compared to `now`.
2. **provision_isolated_network** (vCenter/pyVmomi): ensure an isolated portgroup exists on a
   dedicated vSwitch with no uplink (VLAN `isolated_vlan_id`, default 4090). Idempotent.
3. **start_instant_recovery** (Veeam): call the version-correct instant-recovery endpoint,
   overriding the target network to the isolated portgroup and powering on with NICs
   connected only to that portgroup. Returns `session_id`.
4. **wait_for_recovery_ready** (Veeam + vCenter): poll `GET /sessions/{id}` until the session
   state indicates the mount is published and the VM is registered (`Working` is the correct
   published state for instant-recovery sessions), then resolve the real vCenter moref via
   `SearchIndex.FindByUuid`/`FindByDnsName` or the session's restored-object reference. This
   replaces the placeholder moref.
5. **wait_for_guest_boot** (vCenter): poll `guest.toolsRunningStatus` /
   `guest.guestOperationsReady` until VMware Tools is responsive or a timeout. RTO clock
   starts at step 3 and stops here.
6. **run_health_checks** (WinRM/SSH via existing `health_checks/`): OS boot, service up,
   app-specific probe (SQL integrity, LDAP bind, mail flow), per the workload's runbook.
7. **capture_evidence**: boot screenshot (`CreateScreenshot_Task` -> download from datastore),
   health-check logs, RTO/RPO measurements; upload to the SaaS evidence vault over mTLS.
8. **teardown** (Veeam + vCenter): `stop_instant_recovery` (unpublish), remove the temporary
   VM registration, and leave the isolated portgroup for reuse. Runs in the workflow's
   `finally` path so it executes even on failure.

### API surface used

Veeam B&R REST (auto-detected version prefix `v1.0`/`v1.1`/`v1.2`):
- `POST /api/oauth2/token` (auth, already implemented)
- `GET /api/{v}/backupObjects` and `/restorePoints` (discovery + restore-point selection)
- `POST /api/{v}/restore/instantRecovery/vmware/vm` (v1.2) or
  `/instantRecovery/vmware/vm` (v1.0/v1.1) with network override in the body
- `GET /api/{v}/sessions/{id}` (state polling)
- `POST /api/{v}/instantRecovery/{...}/stopPublishing` (teardown)

vCenter (pyVmomi):
- `ViewManager.CreateContainerView` for inventory
- `SearchIndex.FindByUuid` / `FindByDnsName` to resolve the recovered VM moref
- `HostNetworkSystem` / `DistributedVirtualSwitch` to ensure the isolated portgroup
- `VirtualMachine.guest` for boot/tools status
- `CreateScreenshot_Task` for evidence

### Session-state handling

Introduce an explicit enum mapping for Veeam session states rather than string literals, and
treat `Working` as "published/available" for instant recovery (documented; the earlier QA
review incorrectly flagged this). Any unknown/`unknown` state after N polls fails the
activity with the last observed state in the error, so failures are diagnosable.

## Options Considered

### Option A: Veeam Instant Recovery into isolated vCenter network (chosen)
| Dimension | Assessment |
|---|---|
| Fidelity | High - boots the actual guest, proves real recoverability |
| Speed | Fast - mounts from backup storage, no full restore copy |
| Complexity | Medium - network isolation + session lifecycle |
| Blast radius | Low - isolated portgroup, teardown in `finally` |

### Option B: Full VM restore to a scratch datastore
Pros: simplest API. Cons: slow (full copy), high storage cost, worse RTO signal. Rejected.

### Option C: SureBackup / existing Veeam verification jobs
Pros: Veeam-native isolation. Cons: requires SureBackup licensing and pre-built application
groups per customer; less control over evidence capture and RTO measurement. Rejected for MVP;
revisit as an optional backend.

## Testing Strategy (before live infra)

Because no lab is required to build most of this:
- **Recorded HTTP fixtures** for the Veeam REST client (record real responses once, replay via
  `respx`/`pytest-httpx`) so version detection, restore-point selection, and session polling
  are unit-testable offline.
- **pyVmomi fakes**: thin protocol-level fakes for the handful of managed objects used
  (`SearchIndex`, `VirtualMachine.guest`, portgroup lookup) to test moref resolution and
  boot-wait logic without vCenter.
- **Workflow tests** via Temporal's test environment with activities mocked, asserting the
  step order and that `teardown` always runs.
- A single **live smoke test**, marked `@pytest.mark.live`, gated behind env vars, run only in
  a lab. It stays out of the required CI gates.

## Consequences

**Easier:**
- Real RTO/RPO numbers and evidence, turning the demo into a product.
- The `wait_for_vm_boot` placeholder disappears; recovery status reflects reality.

**Harder / to revisit:**
- Network isolation correctness is customer-topology dependent (standard vSwitch vs DVS);
  the portgroup-provisioning activity needs both paths.
- Veeam version drift: the v1.0/v1.1/v1.2 branching must stay covered by fixtures.
- Teardown must be bulletproof; a leaked instant-recovery mount pins backup storage.

## Action Items

1. [ ] Add recorded Veeam REST fixtures + `respx` tests for version detect, restore-point
       select, session polling.
2. [ ] Implement `resolve_recovered_moref` (replace the placeholder) with pyVmomi fakes + tests.
3. [ ] Implement `provision_isolated_network` for both standard vSwitch and DVS.
4. [ ] Wire RTO/RPO measurement to real timestamps in the workflow.
5. [ ] Implement `capture_evidence` (screenshot + logs) and upload over mTLS.
6. [ ] Ensure `teardown` runs in the workflow `finally` and is idempotent.
7. [ ] Add the gated `@pytest.mark.live` smoke test and a lab runbook in `docs/runbooks/`.
8. [ ] Update the user guide and phase docs when the live path is validated.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
