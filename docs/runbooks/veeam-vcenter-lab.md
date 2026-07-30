# Runbook: Pointing R3VP at a real Veeam B&R + vCenter lab

This runbook covers configuring the appliance's Veeam/vCenter recovery connector
against a real lab and the exact steps to validate the live path that cannot be
exercised offline. See ADR-003 for the design.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

## What is verified offline vs in a lab

Verified offline by the fixture-based unit tests (`tests/test_veeam_rest.py`,
`tests/test_vcenter_moref.py`, `tests/test_veeam_session_states.py`), no server
required:

- Veeam internal capability-tier detection (v1.0 / v1.1 / v1.2) and the
  `x-api-version` header value derived from the build version (11.x -> 1.0-rev1,
  12.x -> 1.1/1.2, 13.0.0 -> 1.3-rev0, 13.0.1+ and 13.1 -> 1.3-rev1).
- OAuth2 token request shaping and response parsing.
- Restore-point discovery path selection and newest-consistent / in-RPO-window
  restore-point selection.
- Instant-recovery endpoint + request-body construction (isolated network
  mapping, power-on), and session-id / stop-publishing path shaping.
- Session-state polling classification for every transition, including the
  failure and no-state (timeout) paths.
- RTO / RPO minute measurement and the 0-100 readiness score.
- vCenter moref lookup-plan ordering and identity extraction from a session body.

Requires a lab to verify (the real-lab boundary):

1. The live OAuth2 token exchange and `serverInfo` shape against the actual
   Veeam build in the lab.
2. The exact JSON shape of the instant-recovery **session body**, specifically
   the restored-object reference. `vcenter/moref.py::parse_recovered_vm_identity`
   reads a set of candidate keys (`restoredObject`/`recoveredObject`/`result`,
   then `instanceUuid`/`biosUuid`/`dnsName`/`name`). Record a real published
   session and confirm/adjust those keys, then replace the fixture
   `tests/fixtures/veeam/session_working.json` with the recorded shape.
3. The pyVmomi `SearchIndex` moref resolution (`VCenterClient.resolve_moref`)
   and isolated-portgroup provisioning on both a standard vSwitch and a DVS
   (`create_isolated_portgroup` / `create_isolated_portgroup_dvs`).
4. `CreateScreenshot_Task` evidence download from the datastore (currently
   returns empty bytes as a placeholder in `vcenter/client.py::take_screenshot`).
5. The exact `x-api-version` revision for Veeam 13.1. `rest.x_api_version` maps
   13.0.1 and later (including 13.1) to `1.3-rev1`, which is the correct floor;
   confirm 13.1 against a live server and, if it ships a newer revision, either
   extend `x_api_version` or pin it via `R3VP_VEEAM_API_VERSION_OVERRIDE`.

Run the lab-only checks with the gated smoke test once implemented
(`@pytest.mark.live`, kept out of the required CI gates).

## Configuration (no hardcoded secrets)

All connection details flow through `ApplianceSettings` (env prefix `R3VP_`,
optionally an `.env` file). Secrets are populated from the SOPS + age vault at
runtime and never committed.

| Setting | Env var | Purpose |
|---|---|---|
| `veeam_base_url` | `R3VP_VEEAM_BASE_URL` | Veeam B&R REST base URL, e.g. `https://vbr-lab-01:9419` |
| `veeam_username` | `R3VP_VEEAM_USERNAME` | Veeam REST service account |
| `veeam_password` | `R3VP_VEEAM_PASSWORD` | Veeam REST password (from vault) |
| `vcenter_host` | `R3VP_VCENTER_HOST` | vCenter FQDN/IP |
| `vcenter_username` | `R3VP_VCENTER_USERNAME` | vCenter user with restore + network rights |
| `vcenter_password` | `R3VP_VCENTER_PASSWORD` | vCenter password (from vault) |
| `vcenter_network_backend` | `R3VP_VCENTER_NETWORK_BACKEND` | `standard` (host vSwitch) or `dvs` |
| `vcenter_vswitch_name` | `R3VP_VCENTER_VSWITCH_NAME` | vSwitch for the isolated portgroup (standard backend) |
| `vcenter_dvs_name` | `R3VP_VCENTER_DVS_NAME` | DVS name (dvs backend) |
| `isolated_vlan_id` | `R3VP_ISOLATED_VLAN_ID` | Isolated VLAN, default 4090 |
| `isolated_network_name` | `R3VP_ISOLATED_NETWORK_NAME` | Portgroup name prefix, default `r3vp-isolated` |
| `recovery_poll_timeout_secs` | `R3VP_RECOVERY_POLL_TIMEOUT_SECS` | Max wait for the mount to publish, default 1800 |
| `recovery_poll_interval_secs` | `R3VP_RECOVERY_POLL_INTERVAL_SECS` | Poll interval, default 10 |

### Example `.env` for a lab (no real secrets committed)

```
R3VP_APPLIANCE_ID=lab-appliance-01
R3VP_ORG_ID=lab-org
R3VP_PROVIDER=vmware
R3VP_VEEAM_BASE_URL=https://vbr-lab-01:9419
R3VP_VEEAM_USERNAME=svc-r3vp
R3VP_VEEAM_PASSWORD=__from_vault__
R3VP_VCENTER_HOST=vcenter-lab-01.corp.local
R3VP_VCENTER_USERNAME=r3vp@vsphere.local
R3VP_VCENTER_PASSWORD=__from_vault__
R3VP_VCENTER_NETWORK_BACKEND=dvs
R3VP_VCENTER_DVS_NAME=DSwitch-Lab
R3VP_ISOLATED_VLAN_ID=4090
```

## Validation sequence in the lab

1. Set the env/vault values above and start the appliance worker.
2. Trigger a `RecoveryTestWorkflow` for a protected VM with recent restore points.
3. Confirm the isolated portgroup is created on the configured backend and has
   no uplink.
4. Confirm instant recovery publishes (session reaches `Working`) and the guest
   boots (VMware Tools responsive).
5. Capture the real session body and finalize the moref-identity key mapping.
6. Confirm teardown (stop-publishing + portgroup handling) runs in the workflow
   `finally` path even on induced failure.
