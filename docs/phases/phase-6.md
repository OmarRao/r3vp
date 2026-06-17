# Phase 6: Extended Hypervisors and Google Cloud

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 6 extends R3VP from 4 infrastructure providers to 10. The new connectors cover the hypervisor platforms most commonly found in enterprise environments outside of VMware and Hyper-V, plus Google Cloud as a third public cloud target alongside Azure and AWS.

New connectors in this phase:

| Connector | Platform | Protocol |
|-----------|----------|----------|
| Proxmox VE | Proxmox Virtual Environment | proxmoxer REST API |
| Nutanix AHV | Nutanix Acropolis Hypervisor | Prism Central v3 REST API |
| RHV / oVirt | Red Hat Virtualization / oVirt | oVirt Engine Python SDK |
| XenServer / Citrix Hypervisor | XenServer 8 / Citrix Hypervisor 8.2 | XenAPI XML-RPC |
| Sangfor HCI | Sangfor Hyper-Converged Infrastructure | Vendor REST API with token auth |
| GCP Backup | Google Cloud Compute Engine | google-cloud-compute + Application Default Credentials |

All six connectors follow the same pattern established in Phase 5: a Python class with `list_vms()`, `create_snapshot()`, `restore_snapshot()`, and `delete_snapshot()` methods, wired into the Temporal activity dispatcher via `detect_provider_vms()`.

---

## Architecture

### Connector Pattern

Every connector lives at `apps/appliance/src/connectors/<provider>/connector.py`. Each implements the same interface:

```python
class BaseConnector:
    def list_vms(self) -> list[VMRecord]: ...
    def create_snapshot(self, vm_id: str, name: str) -> str: ...
    def restore_snapshot(self, vm_id: str, snapshot_id: str) -> None: ...
    def delete_snapshot(self, vm_id: str, snapshot_id: str) -> None: ...
```

The Temporal activity `detect_provider_vms()` reads the `R3VP_PROVIDER` environment variable and routes to the correct connector. Phase 6 extends this routing from 4 providers to 10:

```python
PROVIDER_MAP = {
    "vmware":     VMwareConnector,
    "hyperv":     HyperVConnector,
    "azure":      AzureConnector,
    "aws":        AWSConnector,
    # Phase 6
    "proxmox":    ProxmoxConnector,
    "nutanix":    NutanixConnector,
    "rhv":        RHVConnector,
    "xenserver":  XenServerConnector,
    "sangfor":    SangforConnector,
    "gcp":        GCPConnector,
}
```

### Database Changes

A new `provider_cluster` column is added to the `workloads` table via Alembic migration `0007_provider_cluster.py`. This field stores cluster, pool, or zone metadata specific to each provider:

| Provider | provider_cluster value |
|----------|----------------------|
| Proxmox VE | Proxmox cluster name |
| Nutanix AHV | Prism Central cluster UUID |
| RHV / oVirt | oVirt cluster name |
| XenServer | XenServer pool UUID |
| Sangfor HCI | Sangfor cluster name |
| GCP | GCP project ID + zone (e.g. `my-project/us-central1-a`) |

---

## Connector Reference

### Proxmox VE

**Protocol:** proxmoxer REST API (wraps the Proxmox RESTful API at `https://<host>:8006/api2/json`)

**Auth method:** API token (`PVEAPIToken=user@realm!token-id=<secret>`). Token permissions: PVEVMAdmin on the root `/` path. Service account user: `r3vp@pve`.

**Key methods:**

- `list_vms()`: calls `GET /nodes/{node}/qemu` for each node in the cluster, returns VM ID, name, status, and node.
- `create_snapshot()`: calls `POST /nodes/{node}/qemu/{vmid}/snapshot` with `snapname` and `description`.
- `restore_snapshot()`: calls `POST /nodes/{node}/qemu/{vmid}/snapshot/{snapname}/rollback`.
- `delete_snapshot()`: calls `DELETE /nodes/{node}/qemu/{vmid}/snapshot/{snapname}`.
- `get_pbs_jobs()`: reads Proxmox Backup Server job list from `GET /nodes/{node}/backup` to surface backup job schedules in the workload inventory.

**Install notes:**

```bash
uv add proxmoxer>=2.0
```

Set in `.env`:
```env
R3VP_PROVIDER=proxmox
R3VP_PROXMOX_HOST=proxmox.domain.local
R3VP_PROXMOX_TOKEN_ID=r3vp@pve!r3vp-token
R3VP_PROXMOX_TOKEN_SECRET=<vault: proxmox_token_secret>
R3VP_PROXMOX_VERIFY_SSL=true
```

---

### Nutanix AHV

**Protocol:** Prism Central v3 REST API (`https://<prism-central>:9440/api/nutanix/v3/`)

**Auth method:** HTTP Basic Auth against a Prism Central local user (`r3vp-svc`). Required role: Virtual Machine Viewer plus the ability to trigger recovery point operations. Recommended: create a custom role in Prism Central with VM snapshot and recovery point permissions only.

**Key methods:**

- `list_vms()`: `POST /vms/list` with `kind: vm` filter, pages through results using offset pagination.
- `create_snapshot()`: `POST /vm_recovery_points` with `vm_uuid`, `name`, and `expiration_time`.
- `restore_snapshot()`: `POST /vm_recovery_points/{uuid}/restore`.
- `delete_snapshot()`: `DELETE /vm_recovery_points/{uuid}`.

**Install notes:**

No additional pip dependencies. Prism Central v3 uses standard `httpx` calls already present in the appliance.

Set in `.env`:
```env
R3VP_PROVIDER=nutanix
R3VP_NUTANIX_PC_HOST=prism-central.domain.local
R3VP_NUTANIX_USERNAME=r3vp-svc
R3VP_NUTANIX_PASSWORD=<vault: nutanix_password>
```

---

### RHV / oVirt

**Protocol:** oVirt Engine Python SDK v4 (`ovirt-engine-sdk-python`)

**Auth method:** Username/password authentication against the oVirt Engine REST API (`https://<engine>/ovirt-engine/api`). Service account: `r3vp@internal`. Required role: UserRole on the datacenter with the `create_snapshot`, `restore_vm_from_snapshot`, and `delete_snapshot` action permissions.

**Key methods:**

- `list_vms()`: `connection.system_service().vms_service().list()`, returns VM ID, name, cluster, and status.
- `create_snapshot()`: `vm_service.snapshots_service().add(types.Snapshot(description=name))`.
- `restore_snapshot()`: calls `snapshot_service.restore()` to preview and `vm_service.start()` to commit.
- `delete_snapshot()`: `snapshot_service.remove()`.

**Install notes:**

```bash
uv add ovirt-engine-sdk-python>=4.6
```

Set in `.env`:
```env
R3VP_PROVIDER=rhv
R3VP_RHV_ENGINE_URL=https://rhv-engine.domain.local/ovirt-engine/api
R3VP_RHV_USERNAME=r3vp@internal
R3VP_RHV_PASSWORD=<vault: rhv_password>
R3VP_RHV_CA_BUNDLE=/certs/rhv-ca.pem
```

---

### XenServer / Citrix Hypervisor

**Protocol:** XenAPI XML-RPC over HTTPS (`https://<host>/RPC2`)

**Auth method:** Session token obtained via `session.login_with_password(username, password)`. Service account: `r3vp`. Required role: VM Operator (can snapshot and restore, cannot modify pool config).

**Key methods:**

- `list_vms()`: `VM.get_all_records()` filtered to `is_a_template=False` and `is_control_domain=False`.
- `create_snapshot()`: `VM.snapshot(vm_ref, new_name)` returns a new VM ref representing the snapshot.
- `restore_snapshot()`: `VM.clone(snapshot_ref, new_name)` creates a new VM from the snapshot for isolated testing.
- `delete_snapshot()`: `VM.destroy(snapshot_ref)` after removing attached VDIs.

**Install notes:**

No pip package required. The XenAPI client ships as a single `XenAPI.py` module bundled with XenServer. Copy `XenAPI.py` from your XenServer host at `/usr/lib/python3/dist-packages/XenAPI.py` into `apps/appliance/src/connectors/xenserver/`.

Set in `.env`:
```env
R3VP_PROVIDER=xenserver
R3VP_XEN_HOST=xenserver.domain.local
R3VP_XEN_USERNAME=r3vp
R3VP_XEN_PASSWORD=<vault: xenserver_password>
```

---

### Sangfor HCI

**Protocol:** Sangfor vendor REST API (`https://<management-ip>/api/v1/`)

**Auth method:** Token-based authentication. POST to `/api/v1/auth/login` with `username` and `password` to receive a bearer token. Token lifetime is 1 hour; the connector refreshes automatically before expiry.

**Key methods:**

- `list_vms()`: `GET /api/v1/vms` with pagination via `page` and `page_size` query params.
- `create_snapshot()`: `POST /api/v1/vms/{vm_id}/snapshots` with `name` and `description`.
- `restore_snapshot()`: `POST /api/v1/vms/{vm_id}/snapshots/{snapshot_id}/restore`.
- `delete_snapshot()`: `DELETE /api/v1/vms/{vm_id}/snapshots/{snapshot_id}`.

**Install notes:**

No additional pip dependencies. Uses standard `httpx`.

Set in `.env`:
```env
R3VP_PROVIDER=sangfor
R3VP_SANGFOR_HOST=sangfor-mgmt.domain.local
R3VP_SANGFOR_USERNAME=r3vp
R3VP_SANGFOR_PASSWORD=<vault: sangfor_password>
R3VP_SANGFOR_VERIFY_SSL=true
```

---

### GCP Backup

**Protocol:** Google Cloud Compute Engine REST API via the `google-cloud-compute` Python client library.

**Auth method:** Application Default Credentials (ADC). The appliance calls `google.auth.default()` on startup. In production, the appliance runs as a GCP service account (via Workload Identity on GKE or a service account key file). Required IAM roles: `roles/compute.instanceAdmin.v1` (for snapshot operations) scoped to the target project.

**Key methods:**

- `list_vms()`: `compute_v1.InstancesClient().aggregated_list(project=project_id)`, returns instances across all zones.
- `create_snapshot()`: `compute_v1.DisksClient().create_snapshot(project, zone, disk, snapshot_resource)`.
- `restore_snapshot()`: `compute_v1.InstancesClient().insert()` with a boot disk initialized from the snapshot.
- `delete_snapshot()`: `compute_v1.SnapshotsClient().delete(project, snapshot)`.

**Install notes:**

```bash
uv add google-cloud-compute>=1.14 google-auth>=2.28
```

Set in `.env`:
```env
R3VP_PROVIDER=gcp
R3VP_GCP_PROJECT=my-gcp-project
R3VP_GCP_ZONE=us-central1-a
# For service account key file auth (non-GCP hosted appliance only):
GOOGLE_APPLICATION_CREDENTIALS=/vault/gcp-sa-key.json
```

---

## Database Migration

Migration file: `apps/api/src/db/versions/0007_provider_cluster.py`

```python
def upgrade():
    op.add_column(
        "workloads",
        sa.Column("provider_cluster", sa.String(255), nullable=True),
    )
```

Run with:
```bash
uv run alembic upgrade head
```

---

## Portal Changes

### Provider Coverage Page (`/dashboard/providers`)

The provider grid expands from a 2-column layout (4 cards) to a responsive layout showing all 10 provider cards. Each card retains the same structure from Phase 5: provider icon, name, Active/Inactive badge, workload count, total test runs, average RTO, and a pass rate progress bar.

The page subtitle updates from "4 providers configured" to "10 providers configured" once all connectors are active.

### Extended Hypervisor Support Matrix

A second table is added below the Veeam version support table on the providers page, covering the six new hypervisor platforms:

| Platform | Connector | Snapshot Support | Isolated Recovery | Health Checks |
|----------|-----------|-----------------|-------------------|---------------|
| Proxmox VE 7/8 | proxmoxer REST | Yes | VLAN bridge | Yes |
| Nutanix AHV | Prism Central v3 | Recovery Points | Isolated network | Yes |
| RHV / oVirt 4.5 | oVirt SDK | Yes (preview+commit) | Isolated vNIC | Yes |
| XenServer 8 / Citrix Hypervisor 8.2 | XenAPI XML-RPC | VM clone from snapshot | Isolated network | Yes |
| Sangfor HCI | Vendor REST API | Yes | Isolated vSwitch | Yes |
| GCP Compute Engine | google-cloud-compute | Disk snapshots | Isolated VPC subnet | Yes |

### Dashboard Provider Coverage Widget

The 10-provider coverage widget on the main dashboard shows all 10 providers in two rows of five. Providers without an active connector show as grey.

---

## Installation Dependencies

| Connector | Python Package | Version | Notes |
|-----------|---------------|---------|-------|
| Proxmox VE | proxmoxer | >=2.0 | Add to `apps/appliance/pyproject.toml` |
| Nutanix AHV | (none) | - | Uses httpx, already installed |
| RHV / oVirt | ovirt-engine-sdk-python | >=4.6 | Linux only; requires `libxml2-devel` |
| XenServer | XenAPI.py | - | Copy from XenServer host, not on PyPI |
| Sangfor HCI | (none) | - | Uses httpx, already installed |
| GCP | google-cloud-compute | >=1.14 | Also requires google-auth>=2.28 |

`pyproject.toml` additions for `apps/appliance`:
```toml
[project.optional-dependencies]
proxmox = ["proxmoxer>=2.0"]
rhv = ["ovirt-engine-sdk-python>=4.6"]
gcp = ["google-cloud-compute>=1.14", "google-auth>=2.28"]
```

Install only the providers you need:
```bash
uv sync --extra proxmox --extra gcp
```

---

## R3VP_PROVIDER Accepted Values

```
vmware, hyperv, azure, aws, proxmox, nutanix, rhv, xenserver, sangfor, gcp
```

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
