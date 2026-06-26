# R3VP - Ransomware Readiness and Recovery Validation Platform

## User Guide - v0.2.0 (2026-06-26)

> **R3VP** is free, open-source software that automates ransomware recovery validation for enterprise workloads. It gives security and infrastructure teams continuous, evidence-backed assurance that their backups can actually be restored before an incident forces the question.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Appliance Deployment](#3-appliance-deployment)
4. [Onboarding Wizard](#4-onboarding-wizard)
5. [Dashboard](#5-dashboard)
6. [Workloads](#6-workloads)
7. [Test Runs](#7-test-runs)
8. [Evidence Vault](#8-evidence-vault)
9. [Compliance Frameworks](#9-compliance-frameworks)
10. [Continuous Validation](#10-continuous-validation)
11. [Fleet Management](#11-fleet-management)
12. [MSSP Portal](#12-mssp-portal)
13. [Threat Scanner](#13-threat-scanner)
14. [Multi-Cloud Dashboard](#14-multi-cloud-dashboard)
15. [AI Insights](#15-ai-insights)
16. [Executive Scorecard](#16-executive-scorecard)
17. [Reports](#17-reports)
18. [Runbooks](#18-runbooks)
19. [Team and RBAC](#19-team-and-rbac)
20. [API Keys](#20-api-keys)
21. [SSO Configuration](#21-sso-configuration)
22. [Integrations](#22-integrations)
23. [Audit Log](#23-audit-log)
24. [User Analytics](#24-user-analytics)
25. [API Reference Summary](#25-api-reference-summary)
26. [Database Schema Overview](#26-database-schema-overview)
27. [Security Architecture](#27-security-architecture)
28. [Environment Variables and Configuration](#28-environment-variables-and-configuration)
29. [Upgrade Guide](#29-upgrade-guide)
30. [Troubleshooting](#30-troubleshooting)
31. [Contributing and License](#31-contributing-and-license)

---

## 1. Introduction

### What is R3VP?

R3VP (Ransomware Readiness and Recovery Validation Platform) is an open-source platform that continuously validates enterprise backup and recovery capabilities against ransomware scenarios. Rather than relying on manual, point-in-time disaster recovery tests, R3VP automates the full validation lifecycle: discovering protected workloads, orchestrating test restores against live Veeam Backup and Replication environments, capturing cryptographically signed evidence, and mapping outcomes to compliance frameworks such as SOC 2, ISO 27001, NIST CSF, DORA, PCI-DSS, and HIPAA.

The platform is designed for three primary audiences:

- **Enterprise security teams** who need continuous assurance that recovery objectives (RTO/RPO) are achievable and defensible to auditors.
- **Infrastructure teams** who manage heterogeneous environments spanning VMware, Hyper-V, Azure, AWS, GCP, Proxmox, Nutanix, RHV, XenServer, and Sangfor.
- **MSSPs (Managed Security Service Providers)** who deliver recovery validation as a service to multiple customer organizations from a single multi-tenant portal.

### Design Principles

- **Credential isolation** - Customer credentials never leave the on-premises appliance. All sensitive data is encrypted at rest using SOPS and age.
- **Outbound-only connectivity** - The appliance initiates all connections to the SaaS API over mTLS. No inbound firewall rules are required.
- **Evidence integrity** - Every test result, screenshot, and log file is bundled into a SHA-256 signed evidence package stored in the Evidence Vault.
- **Audit immutability** - The audit log is hash-chained so any tampering is detectable.
- **Open source** - The full platform is freely available. No licensing fees, no vendor lock-in.

### Supported Providers

| Provider | Type | Notes |
|---|---|---|
| VMware vSphere | On-premises hypervisor | vCenter 7.x and 8.x supported |
| Microsoft Hyper-V | On-premises hypervisor | SCVMM and standalone |
| Microsoft Azure | Public cloud | Azure VMs and Azure Backup |
| Amazon Web Services | Public cloud | EC2 and AWS Backup |
| Google Cloud Platform | Public cloud | Compute Engine and GCP Backup |
| Proxmox VE | On-premises hypervisor | API-based integration |
| Nutanix AHV | Hyperconverged | Prism Central API |
| Red Hat Virtualization (RHV) | On-premises hypervisor | oVirt API |
| Citrix XenServer | On-premises hypervisor | XenAPI |
| Sangfor HCI | On-premises hypervisor | Sangfor REST API |

### Veeam B&R API Compatibility

R3VP auto-detects the Veeam Backup and Replication REST API version at connection time and adapts its requests accordingly. Supported API versions:

- v1.0 (VBR 11)
- v1.1 (VBR 12)
- v1.2 (VBR 12.1+)

---

## 2. Architecture Overview

### Component Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER ENVIRONMENT                              │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  R3VP Appliance (Linux VM - Python 3.12+)                       │    │
│  │                                                                  │    │
│  │  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐ │    │
│  │  │ Credential   │  │ Veeam B&R      │  │ Provider Adapters    │ │    │
│  │  │ Vault        │  │ REST Client    │  │ (vSphere, Hyper-V,   │ │    │
│  │  │ (SOPS+age)   │  │ v1.0/1.1/1.2  │  │  Azure, AWS, GCP,    │ │    │
│  │  └──────┬───────┘  └───────┬────────┘  │  Proxmox, Nutanix,   │ │    │
│  │         │                  │           │  RHV, XenServer,     │ │    │
│  │         └──────────────────┴───────────┤  Sangfor)            │ │    │
│  │                                        └──────────────────────┘ │    │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  Temporal.io Worker (workflow execution engine)             │ │    │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────┬─────────────────────────────────┘    │
│                                  │ outbound mTLS only                    │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  R3VP SaaS API      │
                        │  (FastAPI)          │
                        │                     │
                        │  ┌───────────────┐  │
                        │  │ Temporal.io   │  │
                        │  │ Cloud         │  │
                        │  │ (Workflow     │  │
                        │  │  Orchestration│  │
                        │  └───────────────┘  │
                        │                     │
                        │  ┌───────────────┐  │
                        │  │ PostgreSQL    │  │
                        │  │ (primary DB)  │  │
                        │  └───────────────┘  │
                        │                     │
                        │  ┌───────────────┐  │
                        │  │ S3-compatible │  │
                        │  │ Object Store  │  │
                        │  │ (evidence,    │  │
                        │  │  reports)     │  │
                        │  └───────────────┘  │
                        └──────────┬──────────┘
                                   │ HTTPS API
                        ┌──────────▼──────────┐
                        │  R3VP Portal        │
                        │  (Next.js)          │
                        │                     │
                        │  Auth0 (SAML/OIDC)  │
                        │  Firebase Analytics │
                        └─────────────────────┘
```

### Data Flow

1. The appliance pulls encrypted credentials from its local SOPS/age vault.
2. The appliance decrypts credentials in memory and connects to Veeam B&R, the hypervisor, or cloud provider API.
3. Test orchestration signals travel outbound from the appliance to Temporal.io Cloud over mTLS.
4. Temporal.io Cloud coordinates workflow steps across the appliance worker and the SaaS API.
5. Test results, screenshots, and logs are bundled by the appliance into a signed evidence package and uploaded to the SaaS API over mTLS.
6. The SaaS API stores evidence metadata in PostgreSQL and the raw files in object storage.
7. The Portal (Next.js) reads from the SaaS API over HTTPS and presents results to users authenticated via Auth0.
8. Outbound alerts flow from the SaaS API to Slack, PagerDuty, webhooks, and SIEM endpoints.

### Technology Stack Reference

| Component | Technology |
|---|---|
| Appliance runtime | Python 3.12+, managed by uv |
| Appliance credential encryption | SOPS + age |
| Workflow engine | Temporal.io Cloud |
| API backend | FastAPI (Python) |
| API database | PostgreSQL 15+ |
| Evidence / report storage | S3-compatible object store |
| Portal framework | Next.js 14+ |
| Portal authentication | Auth0 (SAML, OIDC) |
| Portal analytics | Firebase Analytics |

---

## 3. Appliance Deployment

The R3VP appliance is a lightweight Python process that runs inside your environment and acts as the secure bridge between your infrastructure and the R3VP SaaS API. It holds all credentials locally and never transmits them externally.

### Prerequisites

| Requirement | Minimum |
|---|---|
| Operating system | Ubuntu 22.04 LTS or RHEL 9 |
| vCPUs | 2 |
| RAM | 4 GB |
| Disk | 40 GB |
| Python | 3.12 or later |
| Network - outbound | HTTPS (443) to `api.r3vp.io` and Temporal.io Cloud endpoints |
| Network - outbound | HTTPS (443) to Veeam B&R server, vCenter, Hyper-V, and cloud provider APIs |
| Network - inbound | None required |

### Step 1 - Provision the VM

Create a Linux VM meeting the prerequisites above. Assign a static IP or stable DHCP reservation. The appliance hostname will be registered in the Portal during onboarding.

### Step 2 - Install Python 3.12 and uv

```bash
# Ubuntu 22.04
sudo apt update && sudo apt install -y python3.12 python3.12-venv curl

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

```bash
# RHEL 9
sudo dnf install -y python3.12 curl
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### Step 3 - Install SOPS and age

SOPS and age are used to encrypt the credential vault at rest. The appliance uses `age` asymmetric encryption so the public key can be stored without risk.

```bash
# Install age
curl -LO https://github.com/FiloSottile/age/releases/latest/download/age-v1.1.1-linux-amd64.tar.gz
tar xzf age-v1.1.1-linux-amd64.tar.gz
sudo mv age/age age/age-keygen /usr/local/bin/

# Install SOPS
curl -LO https://github.com/getsops/sops/releases/latest/download/sops-v3.9.1.linux.amd64
sudo mv sops-v3.9.1.linux.amd64 /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops
```

### Step 4 - Download the Appliance Package

```bash
# Download the latest appliance release
curl -LO https://github.com/omarrao/r3vp/releases/latest/download/r3vp-appliance.tar.gz
tar xzf r3vp-appliance.tar.gz
cd r3vp-appliance

# Install dependencies into a virtual environment via uv
uv venv
uv pip install -r requirements.txt
```

### Step 5 - Generate the age Key Pair

```bash
mkdir -p ~/.r3vp/keys
age-keygen -o ~/.r3vp/keys/appliance.key
# The public key is printed to stdout - copy it for the Portal registration step
cat ~/.r3vp/keys/appliance.key | grep "public key"
```

The private key file (`~/.r3vp/keys/appliance.key`) must remain on the appliance VM. Store it with restricted permissions:

```bash
chmod 600 ~/.r3vp/keys/appliance.key
```

### Step 6 - Register the Appliance in the Portal

1. Log in to the R3VP Portal at `https://app.r3vp.io`.
2. Navigate to **Fleet Management** > **Appliances** > **Register Appliance**.
3. Enter a display name, your organization, and paste the age public key from Step 5.
4. Click **Register**. The Portal generates a registration token and an mTLS client certificate.
5. Download `appliance-cert.pem` and `appliance-key.pem`.

### Step 7 - Configure the Appliance

Place the downloaded certificates in the appliance directory and create the configuration file:

```bash
mkdir -p ~/.r3vp/certs
mv ~/Downloads/appliance-cert.pem ~/.r3vp/certs/
mv ~/Downloads/appliance-key.pem ~/.r3vp/certs/
chmod 600 ~/.r3vp/certs/appliance-key.pem
```

Create `~/.r3vp/config.yaml`:

```yaml
appliance:
  name: "prod-appliance-01"
  organization_id: "org_xxxxxxxxxxxxxxxx"
  registration_token: "tok_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

api:
  base_url: "https://api.r3vp.io"
  cert_path: "~/.r3vp/certs/appliance-cert.pem"
  key_path: "~/.r3vp/certs/appliance-key.pem"

temporal:
  namespace: "r3vp-prod"
  endpoint: "xxxxxxxx.tmprl.cloud:7233"
  tls: true

vault:
  age_key_path: "~/.r3vp/keys/appliance.key"
  vault_path: "~/.r3vp/vault/credentials.enc.yaml"

logging:
  level: "INFO"
  file: "/var/log/r3vp/appliance.log"
```

### Step 8 - Initialize the Credential Vault

The credential vault is a SOPS-encrypted YAML file. Initialize it with an empty structure:

```bash
# Create the vault directory
mkdir -p ~/.r3vp/vault

# Initialize with SOPS encryption using your age public key
# Replace age1... with your actual public key
sops --age age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
     --encrypt \
     /dev/stdin > ~/.r3vp/vault/credentials.enc.yaml << 'EOF'
veeam: {}
providers: {}
EOF
```

Credentials are added to the vault through the Portal's onboarding wizard (see Section 4), which sends encrypted payloads to the appliance that are merged into the vault.

### Step 9 - Start the Appliance

```bash
# Run interactively for initial testing
source .venv/bin/activate
python -m r3vp_appliance --config ~/.r3vp/config.yaml

# Install as a systemd service for production
sudo cp contrib/r3vp-appliance.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now r3vp-appliance
sudo journalctl -u r3vp-appliance -f
```

The appliance will perform a health check on startup, register with Temporal.io Cloud, and appear as **Online** in the Portal's Fleet Management view within 60 seconds.

---

## 4. Onboarding Wizard

The onboarding wizard guides new organizations through a six-step setup process. It launches automatically on first login and can be re-run from **Settings** > **Onboarding**.

![Onboarding](../docs/screenshots/onboarding.png)

### Step 1 - Organization Profile

Configure the basic identity of your organization within R3VP.

| Field | Description | Required |
|---|---|---|
| Organization name | Display name for your org | Yes |
| Industry | Sector classification (Financial, Healthcare, etc.) | Yes |
| Primary compliance frameworks | Select all frameworks you must satisfy | Yes |
| Default RTO target (minutes) | Baseline recovery time objective across all workloads | Yes |
| Default RPO target (hours) | Baseline recovery point objective across all workloads | Yes |
| Contact email | Operational contact for alerts | Yes |
| Time zone | Used for scheduling and report timestamps | Yes |
| Logo (optional) | Displayed on exported reports and the executive scorecard | No |

Click **Save and Continue** to proceed to appliance deployment.

### Step 2 - Deploy Appliance

This step presents the appliance installation instructions tailored to your organization. It provides:

- Your unique `organization_id` and `registration_token` pre-populated for copy-paste.
- Downloadable mTLS certificates once you paste your age public key.
- A **Check Connection** button that polls the API for an appliance heartbeat. The step completes when the appliance is online.

Refer to Section 3 for detailed appliance deployment instructions.

### Step 3 - Connect Veeam

Configure the connection from your appliance to Veeam Backup and Replication.

| Field | Description |
|---|---|
| Veeam B&R server hostname or IP | The server running the Veeam B&R REST API |
| Port | Default 9419 (HTTPS) |
| Username | Service account with read access to all jobs |
| Password | Encrypted client-side before transmission to appliance vault |
| Verify TLS certificate | Toggle off only for self-signed certs in lab environments |
| API version override | Leave on Auto-detect unless troubleshooting |

R3VP tests the connection and auto-detects the API version (v1.0, v1.1, or v1.2). A green checkmark confirms successful authentication. The password is never stored in the Portal; it is encrypted using the appliance's age public key before being sent to the appliance, where it is merged into the SOPS vault.

### Step 4 - Discover Workloads

R3VP queries Veeam B&R and your connected providers to enumerate all protected workloads. Discovery runs as a Temporal workflow on the appliance.

- The discovery scan typically completes within 2 to 10 minutes depending on environment size.
- Each discovered workload is assigned a provider type, a protection status, and initial RPO/RTO defaults from the organization profile.
- Workloads not found in any Veeam backup job are flagged as **Unprotected**.
- You can filter and select which workloads to include in R3VP's scope before proceeding.

### Step 5 - First Test

Run your first recovery validation test to confirm end-to-end connectivity and workflow execution.

1. Select one workload from the discovered list. Choose a non-critical VM for the initial test.
2. Select the test type: **Restore Point Verify** (fastest, no full restore) or **Instant Recovery** (full VM boot test).
3. Click **Run Test**. A Temporal workflow is dispatched to the appliance.
4. The wizard shows a live progress timeline as the test executes.
5. On completion, the pass or fail result is displayed with a link to the evidence bundle.

### Step 6 - Complete

The onboarding summary confirms:

- Appliance online status and version
- Veeam B&R API version detected
- Number of workloads discovered and in scope
- Result of the first test run
- Link to enable Continuous Validation (Section 10)
- Link to configure your first compliance framework assessment (Section 9)

Click **Go to Dashboard** to enter the main application.

---

## 5. Dashboard

The Dashboard is the primary operational view. It synthesizes recovery readiness into a single-page summary with the readiness score, KPIs, recent activity, and trend charts.

![Dashboard](../docs/screenshots/dashboard.png)

### Readiness Score

The readiness score (0 to 100) is a weighted composite metric calculated every 15 minutes from:

| Component | Weight |
|---|---|
| Test pass rate (last 30 days) | 35% |
| RTO compliance rate | 25% |
| Backup coverage (protected workloads / total workloads) | 20% |
| RPO compliance (freshness of last restore point) | 15% |
| Continuous validation streak | 5% |

A score of 80 or above is shown in green. 60 to 79 is amber. Below 60 is red. The score is displayed prominently at the top of the dashboard and is the primary metric used in the Executive Scorecard and compliance framework assessments.

### KPI Cards

| KPI | Description |
|---|---|
| Pass Rate | Percentage of test runs in the last 30 days with a Passed outcome |
| RTO Compliance | Percentage of test runs where actual restore time was within the workload's configured RTO target |
| Coverage | Percentage of in-scope workloads with at least one test run in the last 30 days |
| Streak | Consecutive days with at least one successful validation run |
| Workloads | Count of workloads in scope, with a breakdown by protection status |

### Recent Test Runs

A table of the last 10 test runs shows workload name, provider, test type, outcome (Passed / Failed / Running / Skipped), actual RTO, and a link to the evidence bundle.

### Trend Charts

- **Readiness score over time** - 90-day rolling line chart.
- **Test outcomes by day** - Stacked bar chart (Passed, Failed, Skipped).
- **Coverage by provider** - Donut chart showing workload counts per provider.

### Alert Banner

If any continuous validation checks are in a failing state or if the readiness score has dropped more than 10 points in 24 hours, a red alert banner appears at the top of the dashboard with a summary and a direct link to the affected workloads or checks.

---

## 6. Workloads

The Workloads section provides a full inventory of every protected workload discovered by R3VP, along with their RPO/RTO targets, backup freshness, and test history.

![Workloads](../docs/screenshots/workloads.png)

### Workload List

The workload list is paginated and supports filtering by:

- Provider (vSphere, Hyper-V, Azure, AWS, GCP, Proxmox, Nutanix, RHV, XenServer, Sangfor)
- Protection status (Protected, Unprotected, Excluded)
- RTO compliance status (In compliance, Breached, Never tested)
- RPO compliance status (Fresh, Stale, Critical)
- Backup job name
- Tags

Each row shows:

| Column | Description |
|---|---|
| Workload name | VM, instance, or resource name |
| Provider | Infrastructure platform |
| Backup job | Associated Veeam backup job |
| Last restore point | Timestamp of the most recent backup |
| RPO status | Green (within target), Amber (approaching limit), Red (exceeded) |
| Last test | Date of the most recent validation run |
| Test outcome | Passed, Failed, or Never tested |
| RTO target | Configured recovery time objective |
| Actions | Trigger manual test, edit targets, exclude |

### Workload Detail

Clicking a workload opens its detail panel with:

- Full asset metadata (OS, IP, vCPU, RAM, disk from provider API)
- Backup job assignments and schedule
- RPO and RTO target configuration (editable inline)
- Test run history with outcomes and RTO measurements
- Backup restore point history
- Continuous validation check results
- Applied compliance framework tags

### Editing RPO and RTO Targets

Individual workload targets can override the organization default.

1. Click the edit icon on the RTO or RPO cell.
2. Enter the new target value (RTO in minutes, RPO in hours).
3. Click **Save**. The new target takes effect immediately for compliance calculations and continuous validation alerts.

### Bulk Operations

Select multiple workloads using the checkboxes to:

- Update RTO or RPO targets in bulk.
- Trigger a manual test run for all selected workloads.
- Assign or remove compliance framework tags.
- Exclude selected workloads from R3VP scope.

---

## 7. Test Runs

Test Runs are the core validation mechanism in R3VP. Each test run executes a Temporal.io workflow on the appliance that interacts with Veeam B&R to verify recoverability.

### Test Run Types

| Type | Description | Duration |
|---|---|---|
| Restore Point Verify | Validates backup file integrity using Veeam's built-in verification. No full restore. | 2 to 15 min |
| Instant Recovery | Boots the VM from the backup directly to verify the guest OS comes up and passes health checks. | 5 to 30 min |
| File-Level Restore | Mounts the restore point and verifies that target files can be extracted. | 3 to 20 min |
| Application Item Recovery | Validates application-level recovery (SQL, Exchange, Active Directory). | 10 to 45 min |

### Triggering a Manual Test Run

1. Navigate to **Test Runs** > **New Run**, or click **Test** on any workload row.
2. Select one or more workloads.
3. Choose the test type.
4. Optionally set a label or note for the run.
5. Click **Run Now**. The run is queued as a Temporal workflow.

### Scheduled Test Runs

![Schedule](../docs/screenshots/schedule.png)

Test runs can be scheduled using cron expressions.

1. Navigate to **Test Runs** > **Schedules** > **New Schedule**.
2. Select the workloads or workload groups.
3. Select the test type.
4. Enter a cron expression (e.g., `0 2 * * 0` for every Sunday at 02:00).
5. Set a notification policy (notify on failure, notify always, or silent).
6. Click **Save Schedule**.

Schedules are stored in the SaaS API and dispatched by Temporal.io Cloud to the appliance at the configured time.

### Test Run List

The test run list shows all historical and in-progress runs with pagination. Columns include:

| Column | Description |
|---|---|
| Run ID | Unique identifier (UUID) |
| Workload | Target VM or resource name |
| Provider | Infrastructure platform |
| Test type | Validation method used |
| Status | Running, Passed, Failed, Cancelled |
| Started | Timestamp |
| Duration | Actual wall-clock time |
| Actual RTO | Measured recovery time (for Instant Recovery runs) |
| RTO target | The workload's configured target |
| RTO result | In target or Exceeded |
| Evidence | Link to evidence bundle |

### Test Run Detail

![Test Run Detail](../docs/screenshots/test-run-detail.png)

The test run detail page provides a full breakdown of the run.

#### Timeline

The timeline shows each workflow step with its start time, end time, status, and any output messages:

1. **Initializing** - Appliance receives workflow signal from Temporal.
2. **Credential retrieval** - Appliance decrypts credentials from the vault.
3. **Veeam API authentication** - REST API session established.
4. **Restore point enumeration** - Latest backup selected for the workload.
5. **Test execution** - The specific validation type runs.
6. **Health checks** - Guest OS connectivity verified (for Instant Recovery).
7. **Cleanup** - Temporary recovery infrastructure removed.
8. **Evidence packaging** - Logs, screenshots, and metadata bundled and signed.
9. **Upload** - Evidence package uploaded to the Evidence Vault.
10. **Complete** - Final outcome recorded.

#### Metrics

- Actual RTO (measured in seconds, displayed in minutes)
- Backup age at time of test
- Restore point timestamp used
- Steps passed / failed
- Evidence bundle SHA-256 hash

#### Console Log

![Console](../docs/screenshots/console.png)

The console log tab shows the full verbose output of the workflow execution, including all Veeam API calls and their responses (with credentials redacted).

---

## 8. Evidence Vault

The Evidence Vault stores tamper-evident bundles of proof for every completed test run. These bundles are the primary artifact for compliance audits.

![Evidence Vault](../docs/screenshots/evidence-vault.png)

### Evidence Bundle Contents

Each bundle is a ZIP archive containing:

| File | Description |
|---|---|
| `manifest.json` | Metadata: workload, timestamps, test type, outcome, RTO measurement |
| `workflow_log.txt` | Full console log of the Temporal workflow execution |
| `veeam_api_calls.json` | Redacted Veeam B&R API request/response log |
| `screenshot_*.png` | Screenshots captured during the test (Instant Recovery only) |
| `health_check_results.json` | Guest OS connectivity and application health check results |
| `bundle_sha256.txt` | SHA-256 hash of all other files, signed with the appliance's key |

### Bundle Integrity Verification

The `bundle_sha256.txt` file contains a hash of each file in the bundle. To verify integrity:

```bash
# Download the bundle
curl -O https://api.r3vp.io/v1/evidence/bundles/evid_xxxxxxxx/download \
  -H "Authorization: Bearer $R3VP_API_KEY"

# Verify the hash
unzip evid_xxxxxxxx.zip -d evid_xxxxxxxx
cd evid_xxxxxxxx
sha256sum -c bundle_sha256.txt
```

All files should report `OK`. Any deviation indicates that the bundle has been modified after signing.

### Searching the Evidence Vault

The Evidence Vault supports search and filtering by:

- Date range
- Workload name
- Test outcome (Passed, Failed)
- Test type
- Compliance framework tags

### Evidence Retention

Evidence bundles are retained for 7 years by default to satisfy long-term compliance requirements. Retention policies are configurable per organization in **Settings** > **Evidence Retention**.

### Providing Evidence to Auditors

1. Use the search filters to narrow to the relevant time period and workloads.
2. Select the relevant bundles.
3. Click **Export Selected**. A ZIP of ZIPs is generated.
4. Download and share the export with your auditor.

Alternatively, generate a compliance assessment report (Section 9) which references specific evidence bundles by their SHA-256 hashes.

---

## 9. Compliance Frameworks

R3VP maps recovery validation results to six built-in compliance frameworks and generates scored assessment reports.

![Compliance Frameworks](../docs/screenshots/compliance-frameworks.png)

### Supported Frameworks

| Framework | Full Name | Key Recovery Controls |
|---|---|---|
| SOC 2 | Service Organization Control 2 | CC7.5, A1.2, A1.3 |
| ISO 27001 | ISO/IEC 27001:2022 | Annex A 8.13, 8.14, 5.30 |
| NIST CSF | NIST Cybersecurity Framework 2.0 | RC.RP, RC.CO, PR.IP |
| DORA | Digital Operational Resilience Act | Art. 11, Art. 12, Art. 17 |
| PCI-DSS | Payment Card Industry Data Security Standard v4.0 | Req. 12.3, Req. 12.10 |
| HIPAA | Health Insurance Portability and Accountability Act | 164.308(a)(7), 164.310(d) |

### Compliance Scoring

Each framework is scored on a 0-100 scale using a weighted model. The score components are:

| Component | Description |
|---|---|
| Test pass rate | Percentage of validation tests passing for in-scope workloads |
| RTO compliance | Percentage of workloads meeting documented RTO targets |
| Coverage completeness | Percentage of in-scope workloads tested within the required cadence |
| Evidence availability | Percentage of tests with complete, verified evidence bundles |
| Continuous validation | Whether micro-checks are enabled and passing |
| Documentation completeness | Runbooks configured for in-scope workloads |

Weights vary by framework to reflect their specific requirements. For example, DORA assigns higher weight to RTO compliance because it mandates specific recovery time targets for critical functions.

### Framework Assessment View

The framework assessment page shows:

- Current score with trend (up/down vs. last assessment)
- Breakdown by control category with individual scores
- Failing controls with remediation guidance
- Linked evidence bundles supporting passing controls
- A gap analysis table listing missing or insufficient evidence

### Generating a PDF Assessment Report

1. Navigate to **Compliance Frameworks**.
2. Select the desired framework.
3. Click **Generate Report**.
4. Select the assessment period (typically the last 12 months for annual audits).
5. Optionally add an assessor name and notes.
6. Click **Generate PDF**. The report is queued for generation (typically under 60 seconds).
7. Download the PDF from **Reports** (Section 17) or the email link.

The PDF includes the organization logo, assessment date, score breakdown, control mapping table, and references to evidence bundles by SHA-256 hash.

---

## 10. Continuous Validation

Continuous Validation runs lightweight micro-checks every 15 minutes to maintain real-time visibility into recovery readiness without performing full test restores.

![Continuous Validation](../docs/screenshots/continuous-validation.png)

### Micro-Check Types

| Check | Description | Failure Indicates |
|---|---|---|
| Restore point freshness | Verifies the latest restore point age is within the workload's RPO target | Backup job may have failed or stalled |
| Mount check | Mounts the latest restore point and verifies readability | Backup file corruption or storage issue |
| Veeam job status | Polls the Veeam B&R job state via REST API | Backup job failure or misconfiguration |
| Agent heartbeat | Checks that the Veeam agent on the protected workload is responsive | Agent service stopped or network issue |
| vCenter connectivity | Verifies the appliance can reach vCenter (for vSphere workloads) | Network change or vCenter outage |
| RPO compliance | Calculates time since last successful backup vs. RPO target | Approaching or exceeding the recovery point objective |

### Continuous Validation Policy

A policy defines which checks run for which workloads and the alert thresholds.

To create a policy:

1. Navigate to **Continuous Validation** > **Policies** > **New Policy**.
2. Enter a policy name.
3. Select the target workloads or apply by tag.
4. Enable or disable individual check types.
5. Set the check interval (default 15 minutes; minimum 5 minutes on supported tiers).
6. Configure alert thresholds (e.g., alert if RPO compliance drops below 90%).
7. Select alert destinations (Slack channel, PagerDuty service, email, webhook).
8. Click **Save Policy**.

### Continuous Validation Dashboard

The Continuous Validation section of the Portal shows:

- A summary card per policy with overall health (green, amber, red).
- A per-workload check matrix showing the last result for each check type.
- A timeline of check results over the last 24 hours.
- An alert history for checks that have transitioned to a failing state.

### Alert Rules

Alerts are triggered when a check transitions from passing to failing. Alert rule configuration options:

| Rule | Trigger Condition |
|---|---|
| `readiness_below` | Readiness score drops below a configured threshold |
| `rto_breach` | A test run exceeds the configured RTO target |
| `test_failure` | A validation test run returns a Failed outcome |
| `no_test_in_days` | No test run completed for a workload in N days |
| `threat_detected` | Threat Scanner identifies a ransomware IOC |

Alert destinations are configured per rule and can be different channels for different severity levels.

---

## 11. Fleet Management

Fleet Management provides centralized visibility and control over multiple R3VP appliances. It is primarily used by organizations with multiple sites or by MSSPs managing appliances across customer environments.

![Fleet](../docs/screenshots/fleet.png)

### Appliance Registration

Each appliance is registered with a unique name, organization association, mTLS certificate, and age public key. The Fleet Management view lists all registered appliances with:

| Column | Description |
|---|---|
| Appliance name | Display name set during registration |
| Status | Online, Offline, Degraded |
| Version | Installed appliance package version |
| Last heartbeat | Timestamp of the most recent health ping |
| CPU | Current CPU utilization percentage |
| Memory | Current memory utilization percentage |
| Disk | Current disk utilization percentage |
| Workloads | Number of workloads managed by this appliance |
| Actions | View details, edit, rotate certificate, deregister |

### Appliance Groups

Appliances can be organized into groups for bulk operations and policy assignment.

1. Navigate to **Fleet Management** > **Groups** > **New Group**.
2. Enter a group name (e.g., "Production Sites", "Customer Tier 1").
3. Select the appliances to include.
4. Click **Save Group**.

Groups can be used as targets when configuring continuous validation policies, test schedules, and bulk configuration jobs.

### Health Snapshots

R3VP stores a rolling 30-day history of appliance health metrics (CPU, memory, disk). The health snapshot view shows:

- A line chart of resource utilization over time.
- Alerts for appliances that have exceeded thresholds (CPU > 80%, memory > 85%, disk > 75%).
- Appliance uptime percentage.

### Bulk Configuration Jobs

Bulk configuration jobs apply settings to multiple appliances simultaneously.

Available job types:

| Job Type | Description |
|---|---|
| Update configuration | Push a partial config YAML update to selected appliances |
| Rotate mTLS certificates | Issue new client certificates and trigger appliance rotation |
| Upgrade appliance | Deploy a new appliance package version |
| Sync vault structure | Push vault schema updates without modifying credentials |
| Restart worker | Restart the Temporal worker process on the appliance |

Bulk jobs are dispatched via the Temporal.io workflow engine and report per-appliance success or failure. Job history is retained for 90 days.

---

## 12. MSSP Portal

The MSSP (Managed Security Service Provider) Portal is a multi-tenant layer that allows partner organizations to manage multiple customer organizations from a single interface.

![MSSP](../docs/screenshots/mssp.png)

### MSSP Account Setup

To enable MSSP mode:

1. Contact support@r3vp.io or submit a request through the Portal.
2. Your organization will be upgraded to MSSP tier.
3. The **MSSP Portal** tab becomes visible in the navigation.
4. Assign the `MSSP Manager` role to partner staff members (see Section 19).

### Customer Organization Onboarding

MSSP Managers can create and onboard customer organizations without the customer needing to initiate the process.

1. Navigate to **MSSP Portal** > **Customers** > **Add Customer**.
2. Enter the customer organization name, primary contact email, and industry.
3. Select the default compliance frameworks for the customer.
4. Set RTO and RPO defaults.
5. Click **Create**. An organization is created and an invitation is sent to the customer contact.

The MSSP Manager can complete appliance deployment and onboarding on behalf of the customer, or the customer can log in and complete it themselves.

### Multi-Tenant Dashboard

The MSSP multi-tenant dashboard shows a summary row per customer organization:

| Column | Description |
|---|---|
| Customer name | Organization display name |
| Readiness score | Current composite readiness score (0-100) |
| Last test | Date of the most recent validation run |
| Active alerts | Count of open alert rule violations |
| Appliance status | Online or Offline |
| Workloads | Count of in-scope workloads |

Clicking a customer row opens a full context-switched view of that customer's Portal, maintaining all the same functionality as if logged in directly to that organization.

### MSSP Alert Rules

Alert rules configured at the MSSP level notify partner staff when customer metrics breach thresholds. Available alert rules:

| Rule | Description |
|---|---|
| `readiness_below` | Customer readiness score drops below a configured value |
| `rto_breach` | A customer workload test exceeds its RTO target |
| `test_failure` | A customer validation test run fails |
| `no_test_in_days` | No test run for a customer workload in N days |
| `threat_detected` | Threat Scanner flags a ransomware IOC in a customer environment |

MSSP alert rules are additive: they run in addition to any alert rules configured within individual customer organizations.

---

## 13. Threat Scanner

The Threat Scanner module detects ransomware indicators of compromise (IOCs) in the backup environment by analyzing backup metadata, restore point contents, and protected workloads.

![Threat Scanner](../docs/screenshots/threat-scanner.png)

### What the Threat Scanner Checks

- **Known ransomware file extensions** - Scans restore point file listings for extensions associated with known ransomware families.
- **Encryption entropy analysis** - Flags files with abnormally high entropy that may indicate encryption by ransomware.
- **Honeypot file modification** - Detects changes to monitored canary files placed in protected workloads.
- **Backup chain integrity** - Validates that backup chains have not been disrupted or deleted by ransomware targeting the backup infrastructure.
- **IOC feed matching** - Compares file hashes and network indicators against a continuously updated threat intelligence feed.

### Running a Threat Scan

1. Navigate to **Threat Scanner** > **New Scan**.
2. Select the target workloads or backup jobs.
3. Choose the scan depth (Quick, Standard, Deep).
4. Click **Start Scan**. The scan runs as a Temporal workflow on the appliance.

Scan results are available in the **Threat Scanner** > **Scan History** view.

### Threat Findings

Each finding includes:

- Severity (Critical, High, Medium, Low)
- IOC type (file extension, entropy, honeypot, chain integrity, IOC feed)
- Affected workload and restore point
- Description and recommended action
- Timestamp of detection

Critical and High findings automatically trigger a `threat_detected` alert to configured destinations.

### Providers View

![Providers](../docs/screenshots/providers.png)

The Providers view shows the connection status of all configured infrastructure providers and their contribution to the threat scan surface.

---

## 14. Multi-Cloud Dashboard

The Multi-Cloud Dashboard provides a unified readiness view across all configured cloud and on-premises providers.

![Multi-Cloud Dashboard](../docs/screenshots/multicloud-dashboard.png)

### Provider Readiness Cards

Each configured provider (vSphere, Hyper-V, Azure, AWS, GCP, Proxmox, Nutanix, RHV, XenServer, Sangfor) has a summary card showing:

- Provider readiness score (weighted average of workload scores for that provider)
- Workload count (protected, unprotected, excluded)
- Last test run date and outcome
- Active alert count
- RPO compliance percentage

### Cross-Provider Comparison

A bar chart compares readiness scores across all providers, making it easy to identify which platform has the lowest validation coverage or the highest failure rate.

### Incidents View

![Incidents](../docs/screenshots/incidents.png)

The Incidents view aggregates all active alert rule violations, threat scanner findings, and failed test runs across all providers into a single triage list. Each incident row shows:

| Column | Description |
|---|---|
| Severity | Critical, High, Medium, Low |
| Type | Alert type (test_failure, rto_breach, threat_detected, etc.) |
| Workload | Affected workload name |
| Provider | Infrastructure platform |
| Description | Human-readable summary |
| First seen | Timestamp of first occurrence |
| Status | Open, Acknowledged, Resolved |

Incidents can be acknowledged and resolved directly from this view. Resolution notes are stored in the audit log.

---

## 15. AI Insights

The AI Insights module analyzes historical test results, backup metadata, and compliance scores to generate actionable recovery recommendations.

![AI Insights](../docs/screenshots/ai-insights.png)

### Recommendation Types

| Recommendation | Description |
|---|---|
| Coverage gap | Identifies workloads with no test run in the last N days and suggests scheduling |
| RTO risk | Flags workloads where recent tests are approaching the RTO limit and recommends infrastructure or backup configuration changes |
| Backup freshness risk | Highlights workloads approaching their RPO target based on backup job frequency and recent failures |
| Framework gap | Identifies specific compliance controls with insufficient evidence and recommends targeted tests |
| Provider optimization | Suggests provider-specific configuration changes based on failure patterns |
| Schedule optimization | Recommends test schedule adjustments to improve coverage without overloading the appliance |

### Recommendation Actions

Each recommendation includes:

- **Priority** (Critical, High, Medium, Low) based on the potential impact on the readiness score.
- **Affected workloads** with direct links.
- **Specific action** the user can take to address the gap.
- **Estimated score impact** if the recommendation is implemented.
- A **one-click action** for recommendations that can be automatically configured (e.g., "Enable continuous validation for these workloads").

### Dismissing Recommendations

Recommendations can be dismissed with a note explaining why the recommended action is not applicable. Dismissed recommendations are hidden from the active list but remain visible in the **Dismissed** tab for audit purposes.

---

## 16. Executive Scorecard

The Executive Scorecard provides a C-suite-friendly summary of the organization's ransomware readiness posture, designed for board reporting, executive reviews, and regulatory communications.

![Scorecard](../docs/screenshots/scorecard.png)

### Scorecard Contents

The scorecard is a single-page visual summary containing:

- **Overall readiness score** with trend vs. last period.
- **Key metrics**: test pass rate, RTO compliance, coverage, last test date.
- **Compliance framework scores** for all active frameworks.
- **Top risks**: the three highest-priority open incidents or recommendations.
- **Recovery capability summary**: a plain-language statement of the organization's current validated recovery capability.
- **Trend analysis**: readiness score over the last 90 days.

### Scheduled Delivery

The scorecard can be delivered on a recurring schedule to executive email addresses.

1. Navigate to **Executive Scorecard** > **Delivery Settings**.
2. Enter recipient email addresses.
3. Select the delivery frequency (Weekly, Monthly, Quarterly).
4. Select the delivery day and time.
5. Optionally customize the introductory text.
6. Click **Save**. Delivery uses the organization's configured time zone.

### Manual Export

Click **Export PDF** to generate and download a PDF version of the current scorecard at any time. The PDF includes the organization logo and the generation timestamp.

---

## 17. Reports

The Reports section provides access to all generated compliance assessment reports, executive scorecards, and custom reports.

![Reports](../docs/screenshots/reports.png)

### Report Types

| Report Type | Description |
|---|---|
| Compliance Assessment | Full scored assessment against a specific framework with control mapping |
| Executive Scorecard | C-suite readiness digest (see Section 16) |
| Test Run Summary | Bulk export of test run results for a date range |
| Evidence Export | Packaged evidence bundles for audit delivery |
| Gap Analysis | Specific remediation recommendations with evidence gaps |

### Generating a Report

1. Navigate to **Reports** > **New Report**.
2. Select the report type.
3. Configure the parameters (date range, framework, workloads, etc.).
4. Click **Generate**. Report generation is asynchronous and typically takes 30 to 90 seconds.
5. The report appears in the Reports list when ready.

### Report History

The Reports list shows all generated reports with:

- Report name and type
- Generation date
- Assessment period
- Status (Generating, Ready, Failed)
- File size
- Download link (PDF or ZIP)
- Expiry date (reports expire after 12 months and must be regenerated)

### Compliance Report PDF Structure

A compliance assessment report PDF contains:

1. Cover page with organization name, framework, assessment period, and date generated.
2. Executive summary with overall score and key findings.
3. Score breakdown by control category.
4. Control-by-control table with status, evidence references, and notes.
5. Gap analysis with remediation recommendations.
6. Evidence index listing evidence bundle IDs and SHA-256 hashes.
7. Appendix with raw test run data.

---

## 18. Runbooks

Runbooks are automated recovery playbooks that codify the steps for recovering specific workloads or application stacks. R3VP can execute runbooks as Temporal workflows and record the results.

![Runbooks](../docs/screenshots/runbooks.png)

### Runbook Structure

A runbook consists of an ordered list of steps. Each step has:

| Field | Description |
|---|---|
| Step name | Human-readable label |
| Step type | `veeam_restore`, `health_check`, `notification`, `manual_approval`, `script`, `wait` |
| Target workload | For restore and health check steps |
| Parameters | Type-specific configuration |
| On failure | `stop`, `continue`, or `alert_and_continue` |
| Timeout | Maximum step duration in minutes |

### Creating a Runbook

1. Navigate to **Runbooks** > **New Runbook**.
2. Enter a name and description.
3. Assign target workloads.
4. Add steps using the step builder.
5. Set the runbook trigger: manual only, or triggered automatically on a `threat_detected` alert.
6. Click **Save Runbook**.

### Step Types

**veeam_restore** - Triggers a Veeam instant recovery or restore for a workload.

```yaml
type: veeam_restore
workload: "prod-web-01"
restore_type: "instant_recovery"
restore_point: "latest"
timeout_minutes: 30
```

**health_check** - Verifies that a workload is accessible and healthy after restore.

```yaml
type: health_check
workload: "prod-web-01"
checks:
  - ping
  - tcp_port:443
  - http_200:https://prod-web-01.internal/health
timeout_minutes: 5
```

**notification** - Sends a message to a configured destination.

```yaml
type: notification
destination: "slack:#incident-response"
message: "Runbook step completed: {step_name} for {workload}"
```

**manual_approval** - Pauses the runbook and waits for a human to approve before continuing.

```yaml
type: manual_approval
assigned_to: "security-team"
message: "Please verify that prod-web-01 is healthy before proceeding to restore prod-db-01"
timeout_minutes: 60
```

### Executing a Runbook

![Runbook Execution](../docs/screenshots/runbook-execution.png)

1. Navigate to **Runbooks**.
2. Click **Run** on the desired runbook.
3. Confirm the execution in the dialog.
4. The runbook execution view opens with a live step-by-step progress view.

Each step shows its status (Pending, Running, Passed, Failed, Awaiting Approval), duration, and output log. If a step fails and the on_failure policy is `stop`, the execution halts and an alert is sent.

### Runbook Run History

The run history tab shows all previous executions with:

- Execution ID
- Start and end time
- Overall outcome (Completed, Failed, Stopped)
- Steps passed / failed
- Total duration
- Link to execution evidence bundle (included in the Evidence Vault)

---

## 19. Team and RBAC

R3VP uses role-based access control with five predefined roles and 24 named permissions.

![Team](../docs/screenshots/team.png)

### Roles

| Role | Description |
|---|---|
| Owner | Full administrative access including billing, SSO configuration, and organization deletion |
| Admin | Full operational access. Cannot delete the organization or modify billing. |
| Analyst | Can view all data, trigger test runs, manage runbooks, and generate reports. Cannot modify settings or manage team members. |
| Viewer | Read-only access to all data. Cannot trigger any actions. |
| MSSP Manager | Access to the MSSP Portal for managing customer organizations. Scoped to MSSP functions and customer organizations assigned to them. |

### Permissions Matrix

| Permission | Owner | Admin | Analyst | Viewer | MSSP Manager |
|---|---|---|---|---|---|
| `org:read` | Yes | Yes | Yes | Yes | Yes |
| `org:update` | Yes | Yes | No | No | No |
| `org:delete` | Yes | No | No | No | No |
| `workload:read` | Yes | Yes | Yes | Yes | Yes |
| `workload:update` | Yes | Yes | Yes | No | No |
| `test_run:read` | Yes | Yes | Yes | Yes | Yes |
| `test_run:create` | Yes | Yes | Yes | No | No |
| `test_run:cancel` | Yes | Yes | Yes | No | No |
| `evidence:read` | Yes | Yes | Yes | Yes | Yes |
| `evidence:export` | Yes | Yes | Yes | No | No |
| `compliance:read` | Yes | Yes | Yes | Yes | Yes |
| `compliance:update` | Yes | Yes | No | No | No |
| `report:read` | Yes | Yes | Yes | Yes | Yes |
| `report:create` | Yes | Yes | Yes | No | No |
| `runbook:read` | Yes | Yes | Yes | Yes | No |
| `runbook:create` | Yes | Yes | Yes | No | No |
| `runbook:execute` | Yes | Yes | Yes | No | No |
| `team:read` | Yes | Yes | Yes | No | No |
| `team:update` | Yes | Yes | No | No | No |
| `api_key:manage` | Yes | Yes | No | No | No |
| `sso:manage` | Yes | No | No | No | No |
| `integration:manage` | Yes | Yes | No | No | No |
| `audit_log:read` | Yes | Yes | Yes | No | No |
| `mssp:manage` | Yes | Yes | No | No | Yes |

### Inviting Team Members

1. Navigate to **Team** > **Invite Member**.
2. Enter the user's email address.
3. Select their role.
4. Click **Send Invitation**.

The user receives an email invitation with a time-limited activation link. If SSO is configured, the user is automatically provisioned on first login with the assigned role.

### Removing Team Members

1. Navigate to **Team**.
2. Click the menu icon on the member's row.
3. Select **Remove Member**.
4. Confirm. Active sessions for that user are immediately invalidated.

---

## 20. API Keys

R3VP API keys allow programmatic access to the SaaS API from external systems, scripts, and integrations.

![API Keys](../docs/screenshots/api-keys.png)

### Key Security Model

- API keys are generated using a cryptographically secure random generator.
- The full key is shown only once at creation time. It is immediately hashed (SHA-256) before storage.
- R3VP stores only the SHA-256 hash. The original key cannot be recovered; if lost, the key must be rotated.
- Each key can be scoped to a subset of the 24 named permissions.

### Creating an API Key

1. Navigate to **Settings** > **API Keys** > **New API Key**.
2. Enter a descriptive name (e.g., "CI/CD pipeline", "SIEM integration").
3. Select the permissions to grant the key. Follow the principle of least privilege.
4. Optionally set an expiry date (recommended for time-limited integrations).
5. Click **Create Key**.
6. Copy the displayed key immediately. It will not be shown again.

### Using API Keys

Include the key in the `Authorization` header:

```bash
curl https://api.r3vp.io/v1/workloads \
  -H "Authorization: Bearer r3vp_sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### Rotating a Key

1. Navigate to **Settings** > **API Keys**.
2. Click **Rotate** on the key to rotate.
3. A new key is generated and displayed. The old key is immediately invalidated.
4. Update all systems using the old key with the new value.

### Key List

The API Key list shows:

| Column | Description |
|---|---|
| Name | Key display name |
| Created | Creation timestamp |
| Last used | Timestamp of the most recent API request |
| Permissions | Granted permission set |
| Expiry | Expiry date or "Never" |
| Status | Active or Expired |
| Actions | Rotate, Revoke |

---

## 21. SSO Configuration

R3VP supports enterprise Single Sign-On via SAML 2.0 and OIDC through Auth0.

![SSO](../docs/screenshots/sso.png)

### Supported Identity Providers

- Microsoft Entra ID (Azure AD) - SAML and OIDC
- Okta - SAML and OIDC
- Google Workspace - OIDC
- PingFederate - SAML
- Any SAML 2.0 or OIDC-compliant provider

### SAML Configuration

1. Navigate to **Settings** > **SSO** > **Configure SAML**.
2. Note the **SP Entity ID** and **ACS URL** provided by R3VP.
3. Create a SAML application in your identity provider using these values.
4. Download the IdP metadata XML from your identity provider.
5. In R3VP, paste the **IdP Metadata XML** or enter the individual IdP values:
   - IdP Entity ID
   - IdP SSO URL
   - IdP Certificate (PEM)
6. Configure attribute mappings:

| SAML Attribute | R3VP Field |
|---|---|
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` | Email |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name` | Display name |
| `groups` | Role mapping (optional) |

7. Optionally configure group-to-role mapping to automatically assign R3VP roles based on IdP group membership.
8. Click **Save and Test**. R3VP performs a test authentication flow.

### OIDC Configuration

1. Navigate to **Settings** > **SSO** > **Configure OIDC**.
2. Create an OIDC application in your identity provider.
3. Set the **Redirect URI** to the value shown in R3VP.
4. Enter the **Client ID**, **Client Secret**, and **Issuer URL** from your identity provider.
5. Configure scope and claims mapping.
6. Click **Save and Test**.

### SSO Enforcement

Once SSO is configured and tested, you can enforce it by enabling **Require SSO** in the SSO settings. This prevents team members from logging in with password-based authentication. Owners retain an emergency bypass via a one-time token process.

### Just-in-Time Provisioning

When JIT provisioning is enabled, users who authenticate via SSO for the first time are automatically created in R3VP with the **Viewer** role (or a role mapped from their IdP groups). This eliminates the need to pre-invite users individually.

---

## 22. Integrations

R3VP integrates with Slack, PagerDuty, generic webhooks, and SIEM platforms to deliver alerts and events to your existing toolchain.

![Integrations](../docs/screenshots/integrations.png)

### Slack Integration

1. Navigate to **Settings** > **Integrations** > **Slack**.
2. Click **Connect to Slack** and authorize the R3VP Slack app in your workspace.
3. Select the default channel for notifications.
4. Configure per-alert-type channel overrides (e.g., Critical alerts to `#security-incidents`, informational to `#backup-ops`).
5. Click **Save**.

Slack messages include a summary of the event, severity, affected workload, and a direct link to the Portal for details.

### PagerDuty Integration

1. Navigate to **Settings** > **Integrations** > **PagerDuty**.
2. Obtain an Integration Key from PagerDuty (Events API v2).
3. Paste the Integration Key into R3VP.
4. Configure the severity mapping:

| R3VP Alert Severity | PagerDuty Severity |
|---|---|
| Critical | critical |
| High | error |
| Medium | warning |
| Low | info |

5. Click **Save and Test**. A test event is sent to PagerDuty.

### Webhook Integration

Webhooks deliver a JSON payload to any HTTPS endpoint on alert events.

1. Navigate to **Settings** > **Integrations** > **Webhooks** > **Add Webhook**.
2. Enter the destination URL.
3. Optionally enter a shared secret for HMAC-SHA256 request signing.
4. Select the event types to deliver.
5. Click **Save**.

Webhook payload format:

```json
{
  "event_id": "evt_xxxxxxxxxxxxxxxx",
  "event_type": "test_failure",
  "timestamp": "2026-06-26T14:32:00Z",
  "organization_id": "org_xxxxxxxxxxxxxxxx",
  "severity": "high",
  "workload": {
    "id": "wkl_xxxxxxxxxxxxxxxx",
    "name": "prod-web-01",
    "provider": "vsphere"
  },
  "details": {
    "test_run_id": "run_xxxxxxxxxxxxxxxx",
    "failure_reason": "Restore point mount failed",
    "rto_actual_minutes": null,
    "rto_target_minutes": 60
  },
  "portal_url": "https://app.r3vp.io/test-runs/run_xxxxxxxxxxxxxxxx"
}
```

The `X-R3VP-Signature` header contains `sha256=<hmac_hex>` for request verification.

### SIEM Integration

R3VP can forward structured events to SIEM platforms via:

- **Syslog (CEF format)** - Common Event Format for Splunk, ArcSight, and QRadar.
- **HTTP/S JSON stream** - For Elastic Security, Microsoft Sentinel, and Sumo Logic.

Navigate to **Settings** > **Integrations** > **SIEM** to configure the destination and format.

---

## 23. Audit Log

The Audit Log records every user action and system event in R3VP in a tamper-evident, hash-chained log.

### Hash Chain Architecture

Each audit log entry contains:

- Event ID (UUID)
- Timestamp (UTC, millisecond precision)
- Actor (user ID or API key ID)
- Action (e.g., `test_run.created`, `user.invited`, `api_key.rotated`)
- Resource type and ID
- IP address and user agent
- Event payload (JSON)
- SHA-256 hash of the previous entry (`prev_hash`)
- SHA-256 hash of this entry

The chain can be verified by recalculating each entry's hash and confirming it matches the `prev_hash` recorded in the next entry. Any insertion, deletion, or modification of a historical entry will break the chain from that point forward.

### Accessing the Audit Log

Navigate to **Settings** > **Audit Log**. The log is paginated with 50 entries per page and supports filtering by:

- Date range
- Actor (user or API key)
- Action type
- Resource type

### Audit Log Export

The full audit log can be exported as a JSON Lines file for import into SIEM systems or for offline verification.

1. Navigate to **Settings** > **Audit Log** > **Export**.
2. Select the date range.
3. Click **Export JSON**. The export is queued and available for download within a few minutes.

### Verifying the Audit Log Chain

```bash
# Download the audit log export
curl -O https://api.r3vp.io/v1/audit/export?from=2026-01-01&to=2026-06-26 \
  -H "Authorization: Bearer $R3VP_API_KEY"

# Verify the chain using the R3VP CLI
r3vp audit verify --file audit_export.jsonl
# Expected output: "Chain verified: 14,832 entries, chain intact"
```

---

## 24. User Analytics

R3VP uses Firebase Analytics to track login activity, session behavior, and feature usage. This data is used to understand platform adoption, improve the user experience, and identify unused features.

![Analytics](../docs/screenshots/analytics.png)

### Tracked Events

| Event | Description |
|---|---|
| `user_login` | User authentication via password or SSO |
| `session_start` | Browser session initiated |
| `session_end` | Browser session terminated or expired |
| `feature_viewed` | User navigates to a feature section |
| `test_run_triggered` | Manual test run initiated from Portal |
| `report_generated` | Compliance or scorecard report generated |
| `runbook_executed` | Runbook execution started |
| `evidence_exported` | Evidence bundle download initiated |

### Analytics Dashboard

The analytics dashboard (visible to Owner and Admin roles) shows:

- Daily active users (DAU) over the last 30 days
- Session count and average session duration
- Feature engagement breakdown (which sections are most used)
- Login method distribution (password vs. SSO)
- Top users by session count

### Privacy and Data Handling

Analytics events are attributed to user IDs, not names or email addresses, within Firebase. Email addresses are stored in R3VP's own database and are never sent to Firebase. The analytics data is used solely for product improvement and is not shared with third parties. Users in organizations that have enabled SSO will have their Firebase user ID scoped to their organization.

---

## 25. API Reference Summary

The R3VP SaaS API is a RESTful HTTP API documented with OpenAPI 3.1. The full interactive API documentation is available at `https://api.r3vp.io/docs`.

### Authentication

All API requests must include an `Authorization: Bearer <token>` header. Tokens are either:

- **User JWTs** - Short-lived tokens issued by Auth0 on login. Used by the Portal.
- **API Keys** - Long-lived scoped keys created in the Portal (see Section 20).

### Base URL

```
https://api.r3vp.io/v1
```

### Key Endpoints

#### Workloads

| Method | Endpoint | Description |
|---|---|---|
| GET | `/workloads` | List all workloads with pagination and filtering |
| GET | `/workloads/{id}` | Get a single workload with full detail |
| PATCH | `/workloads/{id}` | Update RTO/RPO targets or tags |
| POST | `/workloads/discover` | Trigger a workload discovery scan |

#### Test Runs

| Method | Endpoint | Description |
|---|---|---|
| GET | `/test-runs` | List test runs with filtering |
| POST | `/test-runs` | Create and trigger a new test run |
| GET | `/test-runs/{id}` | Get full test run detail including timeline |
| DELETE | `/test-runs/{id}` | Cancel an in-progress test run |

#### Evidence

| Method | Endpoint | Description |
|---|---|---|
| GET | `/evidence` | List evidence bundles |
| GET | `/evidence/{id}` | Get evidence bundle metadata |
| GET | `/evidence/{id}/download` | Download the signed evidence bundle ZIP |

#### Compliance

| Method | Endpoint | Description |
|---|---|---|
| GET | `/compliance/frameworks` | List available compliance frameworks |
| GET | `/compliance/assessments` | List assessments with scores |
| POST | `/compliance/assessments` | Generate a new assessment |

#### Continuous Validation

| Method | Endpoint | Description |
|---|---|---|
| GET | `/cv/policies` | List continuous validation policies |
| POST | `/cv/policies` | Create a new policy |
| GET | `/cv/results` | Get recent micro-check results |

#### Fleet

| Method | Endpoint | Description |
|---|---|---|
| GET | `/fleet/appliances` | List registered appliances |
| GET | `/fleet/appliances/{id}` | Get appliance detail and health |
| POST | `/fleet/appliances/{id}/jobs` | Submit a bulk config job |

#### Runbooks

| Method | Endpoint | Description |
|---|---|---|
| GET | `/runbooks` | List runbooks |
| POST | `/runbooks` | Create a runbook |
| POST | `/runbooks/{id}/execute` | Execute a runbook |
| GET | `/runbooks/{id}/runs` | Get run history for a runbook |

#### Audit Log

| Method | Endpoint | Description |
|---|---|---|
| GET | `/audit` | Paginated audit log with filtering |
| GET | `/audit/export` | Export audit log as JSON Lines |

### Rate Limiting

API requests are rate-limited per API key:

| Tier | Requests per minute |
|---|---|
| Default | 120 |
| Elevated (available on request) | 600 |

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 118
X-RateLimit-Reset: 1751000460
```

### Error Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "WORKLOAD_NOT_FOUND",
    "message": "Workload with ID wkl_xxxxxxxx was not found in this organization",
    "request_id": "req_xxxxxxxxxxxxxxxx"
  }
}
```

---

## 26. Database Schema Overview

R3VP uses PostgreSQL as its primary database. The schema is managed via Alembic migrations.

### Core Tables

| Table | Description |
|---|---|
| `organizations` | Organization records with settings and defaults |
| `users` | User accounts with role assignments |
| `api_keys` | SHA-256 hashed API key records |
| `appliances` | Registered appliance records with mTLS cert metadata |
| `workloads` | Discovered workload inventory with RPO/RTO targets |
| `test_runs` | Test run records with outcomes and measurements |
| `test_run_steps` | Individual step records within test runs |
| `evidence_bundles` | Evidence bundle metadata and SHA-256 hashes |
| `cv_policies` | Continuous validation policy definitions |
| `cv_results` | Micro-check result history |
| `compliance_frameworks` | Framework definitions and control mappings |
| `compliance_assessments` | Scored assessment records |
| `runbooks` | Runbook definitions |
| `runbook_runs` | Runbook execution history |
| `audit_log` | Hash-chained audit entries |
| `integrations` | Integration configurations (Slack, PagerDuty, etc.) |
| `alert_rules` | Alert rule definitions |
| `fleet_groups` | Appliance group definitions |
| `reports` | Generated report metadata and storage paths |

### Key Relationships

```
organizations
  ├── users (many)
  ├── api_keys (many)
  ├── appliances (many)
  ├── workloads (many)
  │     ├── test_runs (many)
  │     │     └── test_run_steps (many)
  │     │     └── evidence_bundles (one)
  │     └── cv_results (many)
  ├── cv_policies (many)
  ├── compliance_assessments (many)
  ├── runbooks (many)
  │     └── runbook_runs (many)
  └── audit_log (many)
```

---

## 27. Security Architecture

### Credential Isolation

Credentials for Veeam B&R, vCenter, Hyper-V, and cloud providers never leave the customer's on-premises appliance. The credential lifecycle is:

1. During onboarding, the user enters credentials in the Portal.
2. The Portal encrypts the credential payload using the appliance's age public key (which was registered during appliance setup and is stored in the Portal).
3. The encrypted payload is sent to the appliance over the mTLS API connection.
4. The appliance decrypts the payload using its private age key and merges it into the SOPS-encrypted vault on disk.
5. When a workflow needs a credential, the appliance decrypts it in memory, uses it, and clears it from memory when done.
6. The SaaS API and Portal never hold plaintext credentials.

### Outbound-Only mTLS

The appliance initiates all connections. The firewall rules required are:

- Outbound HTTPS (443) to `api.r3vp.io`
- Outbound to Temporal.io Cloud endpoints (see Temporal.io documentation for current IP ranges)
- No inbound rules required for R3VP

All appliance-to-API connections use mTLS (mutual TLS). Both parties present certificates:

- The appliance presents its client certificate (issued during registration).
- The API presents its server certificate.
- Both are verified before any data is exchanged.

### Hash-Chained Audit Log

The audit log hash chain makes it impossible to silently tamper with historical records. Any modification (insert, update, delete) breaks the chain from the modified entry forward. Verification can be performed offline using an exported JSON Lines file.

### SHA-256 API Keys

API keys are only ever stored as SHA-256 hashes. If the database is compromised, the attacker cannot recover the original keys. Keys must be rotated after any suspected database compromise.

### RBAC Enforcement

All API endpoints enforce permission checks at the handler level. Permission checks use the caller's resolved permission set (derived from role plus any key-level scoping). Resource access is further scoped by `organization_id` to prevent cross-tenant data access.

### Evidence Integrity

Evidence bundles are signed at creation time on the appliance using a keyed SHA-256 HMAC. The signature is stored in `bundle_sha256.txt` within the bundle. Any modification to bundle files after signing is detectable by re-running the verification.

---

## 28. Environment Variables and Configuration

### Appliance Configuration Reference

The appliance `config.yaml` supports the following fields:

| Key | Default | Description |
|---|---|---|
| `appliance.name` | Required | Display name of this appliance instance |
| `appliance.organization_id` | Required | Organization ID from the Portal |
| `appliance.registration_token` | Required | Registration token from the Portal |
| `api.base_url` | `https://api.r3vp.io` | SaaS API base URL |
| `api.cert_path` | Required | Path to the mTLS client certificate |
| `api.key_path` | Required | Path to the mTLS client private key |
| `api.timeout_seconds` | `30` | HTTP request timeout |
| `temporal.namespace` | Required | Temporal.io Cloud namespace |
| `temporal.endpoint` | Required | Temporal.io Cloud gRPC endpoint |
| `temporal.tls` | `true` | Enable TLS for Temporal connection |
| `vault.age_key_path` | Required | Path to the age private key file |
| `vault.vault_path` | Required | Path to the SOPS-encrypted credential vault |
| `logging.level` | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR |
| `logging.file` | `/var/log/r3vp/appliance.log` | Log output file path |
| `worker.max_concurrent_workflows` | `5` | Maximum simultaneous Temporal workflows |
| `worker.max_concurrent_activities` | `20` | Maximum simultaneous Temporal activities |

### SaaS API Environment Variables

The following environment variables configure the SaaS API deployment:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string (for session cache) |
| `TEMPORAL_NAMESPACE` | Yes | Temporal.io Cloud namespace |
| `TEMPORAL_ENDPOINT` | Yes | Temporal.io Cloud gRPC endpoint |
| `TEMPORAL_TLS_CERT` | Yes | mTLS certificate for Temporal connection |
| `TEMPORAL_TLS_KEY` | Yes | mTLS private key for Temporal connection |
| `S3_BUCKET_NAME` | Yes | Object storage bucket for evidence and reports |
| `S3_ENDPOINT_URL` | No | S3-compatible endpoint (omit for AWS S3) |
| `S3_ACCESS_KEY_ID` | Yes | Object storage access key |
| `S3_SECRET_ACCESS_KEY` | Yes | Object storage secret key |
| `AUTH0_DOMAIN` | Yes | Auth0 tenant domain |
| `AUTH0_AUDIENCE` | Yes | Auth0 API audience identifier |
| `AUTH0_CLIENT_ID` | Yes | Auth0 machine-to-machine client ID |
| `AUTH0_CLIENT_SECRET` | Yes | Auth0 machine-to-machine client secret |
| `ENCRYPTION_KEY` | Yes | 32-byte hex key for symmetric encryption of vault payloads in transit |
| `AUDIT_HMAC_KEY` | Yes | 32-byte hex key for audit log HMAC signing |
| `SENTRY_DSN` | No | Sentry error tracking DSN |
| `LOG_LEVEL` | `INFO` | Application log level |
| `CORS_ORIGINS` | Yes | Comma-separated list of allowed CORS origins |

### Portal Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | SaaS API base URL |
| `NEXT_PUBLIC_AUTH0_DOMAIN` | Yes | Auth0 tenant domain |
| `NEXT_PUBLIC_AUTH0_CLIENT_ID` | Yes | Auth0 SPA client ID |
| `NEXT_PUBLIC_AUTH0_AUDIENCE` | Yes | Auth0 API audience |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Yes | Firebase Analytics API key |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Yes | Firebase app ID |

---

## 29. Upgrade Guide

### Versioning Policy

R3VP follows semantic versioning:

- **Major versions** (e.g., 1.0.0 to 2.0.0) may include breaking API changes. Migration guides are published.
- **Minor versions** (e.g., 0.1.0 to 0.2.0) add new features and are backward compatible.
- **Patch versions** (e.g., 0.2.0 to 0.2.1) contain bug fixes only.

The current version is **v0.2.0** (2026-06-26).

### Checking the Current Version

```bash
# Appliance version
python -m r3vp_appliance --version

# API version (via endpoint)
curl https://api.r3vp.io/v1/version
```

### Upgrading the Appliance

1. Check the release notes at `https://github.com/omarrao/r3vp/releases` for any breaking changes or migration steps.
2. Download the new release:

```bash
curl -LO https://github.com/omarrao/r3vp/releases/download/v0.2.0/r3vp-appliance.tar.gz
tar xzf r3vp-appliance.tar.gz -C /opt/r3vp-appliance --strip-components=1
```

3. Update dependencies:

```bash
cd /opt/r3vp-appliance
uv pip install -r requirements.txt
```

4. Restart the appliance service:

```bash
sudo systemctl restart r3vp-appliance
sudo journalctl -u r3vp-appliance -f
```

5. Verify the new version is running and the appliance shows as Online in the Fleet Management view.

### Database Migrations

Database migrations are run automatically when the SaaS API starts. For self-hosted deployments, run migrations manually:

```bash
# From the API project directory
alembic upgrade head
```

Always back up the PostgreSQL database before running migrations for minor or major version upgrades.

### Rollback Procedure

If an upgrade introduces a regression:

1. Stop the appliance service.
2. Restore the previous release from the backup archive or re-download the previous version.
3. Run `alembic downgrade -1` to revert the last database migration (if applicable).
4. Restart the appliance service.
5. File a bug report at `https://github.com/omarrao/r3vp/issues`.

---

## 30. Troubleshooting

### Appliance Shows as Offline

**Symptoms:** The Fleet Management view shows the appliance as Offline. Workflows are not executing.

**Diagnosis:**

```bash
# Check the service is running
sudo systemctl status r3vp-appliance

# Check the appliance logs
sudo journalctl -u r3vp-appliance --since "1 hour ago"

# Test connectivity to the API
curl -v --cert ~/.r3vp/certs/appliance-cert.pem \
       --key ~/.r3vp/certs/appliance-key.pem \
       https://api.r3vp.io/v1/health
```

**Common causes and fixes:**

| Cause | Fix |
|---|---|
| mTLS certificate expired | Rotate the certificate via Fleet Management > Rotate Certificate, then re-download and replace the cert files on the appliance |
| DNS resolution failure | Verify the appliance can resolve `api.r3vp.io`. Check `/etc/resolv.conf` and firewall DNS rules. |
| Outbound HTTPS blocked | Verify the firewall allows outbound TCP 443 to `api.r3vp.io` and Temporal.io Cloud endpoints |
| Appliance service crashed | Check logs for Python tracebacks. Common cause is a malformed `config.yaml`. |

### Veeam API Authentication Fails

**Symptoms:** The onboarding Step 3 connection test fails with an authentication error. Test runs fail at the "Veeam API authentication" step.

**Diagnosis:**

```bash
# Check vault is readable
sops --decrypt ~/.r3vp/vault/credentials.enc.yaml | python3 -c "import sys,json; d=__import__('yaml').safe_load(sys.stdin); print('Vault OK, veeam key present:', 'veeam' in d)"

# Test Veeam API directly from the appliance
curl -k -X POST https://YOUR_VEEAM_SERVER:9419/api/oauth2/token \
  -d 'grant_type=password&username=YOUR_USER&password=YOUR_PASS'
```

**Common causes and fixes:**

| Cause | Fix |
|---|---|
| Wrong password in vault | Re-enter credentials via Settings > Veeam Connection > Update Credentials |
| Veeam B&R REST API service not running | On the Veeam server, verify the Veeam Backup REST API Service is running in Windows Services |
| Self-signed certificate | Set `verify_tls: false` in the Veeam connection settings (lab environments only) |
| API version mismatch | Force the API version to the correct value in the connection settings |

### Test Runs Stall or Time Out

**Symptoms:** A test run shows as Running indefinitely and never completes. The timeline shows an early step as Running without progression.

**Diagnosis:**

```bash
# Check Temporal workflow status
r3vp workflow status --run-id RUN_ID_HERE

# Check for Temporal worker errors
sudo journalctl -u r3vp-appliance | grep -i "temporal\|workflow\|activity"
```

**Common causes and fixes:**

| Cause | Fix |
|---|---|
| Temporal.io Cloud connectivity lost | Check outbound connectivity to Temporal endpoints. Restart the appliance service. |
| Veeam task queue full | Check the Veeam B&R console for queued or stuck jobs. Reduce `max_concurrent_workflows` in appliance config if overloading Veeam. |
| Instant recovery cleanup stuck | Manually verify and remove any orphaned instant recovery instances in the Veeam console. Cancel the stuck run in R3VP. |
| Appliance ran out of disk | Check disk usage. Evidence bundles are stored temporarily during packaging. Free disk space and retry. |

### Compliance Score Not Updating

**Symptoms:** The compliance framework score has not changed despite new passing test runs.

**Cause and fix:** Compliance scores are recalculated on a schedule (every 6 hours). To force an immediate recalculation, navigate to **Compliance Frameworks**, select the framework, and click **Recalculate Now**.

### Audit Log Chain Verification Fails

**Symptoms:** Running `r3vp audit verify` reports a chain break.

**Cause:** This indicates that one or more audit log entries have been modified, deleted, or inserted out of order. This is a security event.

**Response:**

1. Note the entry ID where the chain breaks.
2. Check the API server logs for any database errors or anomalies around the timestamp of the broken entry.
3. Compare the exported log against any backup of the PostgreSQL `audit_log` table.
4. Contact security@r3vp.io if you suspect unauthorized database access.

### Evidence Bundle Verification Fails

**Symptoms:** `sha256sum -c bundle_sha256.txt` reports one or more files with FAILED status.

**Cause:** The evidence bundle was modified after signing. This may indicate a storage integrity issue or tampering.

**Response:**

1. Download the bundle again from the API to rule out download corruption.
2. If the re-downloaded bundle also fails verification, file a support issue.
3. Do not use a bundle that fails verification in compliance submissions.

---

## 31. Contributing and License

### Contributing

R3VP welcomes contributions from the community. To contribute:

1. Fork the repository at `https://github.com/omarrao/r3vp`.
2. Create a feature branch from `main`.
3. Make your changes with tests.
4. Open a pull request with a clear description of the change and the problem it solves.

Please review the `CONTRIBUTING.md` file in the repository for code style guidelines, the test suite setup, and the PR review process.

For security vulnerabilities, do not open a public GitHub issue. Email security@r3vp.io with a description of the vulnerability and steps to reproduce. Security reports are acknowledged within 48 hours.

### Bug Reports

File bug reports at `https://github.com/omarrao/r3vp/issues` using the bug report template. Include:

- R3VP version (appliance and Portal)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant log output (redact any credentials)

### Feature Requests

Feature requests are welcomed as GitHub issues using the feature request template. Describe the use case and the problem the feature would solve.

### License

R3VP is licensed under the Apache License 2.0. See the `LICENSE` file in the repository for the full text.

```
Copyright 2026 Omar Rao

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## Appendix A - Compliance Control Mapping Quick Reference

### SOC 2 Controls Addressed

| Control | Description | R3VP Feature |
|---|---|---|
| CC7.5 | Recovery and incident response procedures tested | Test Runs, Evidence Vault |
| A1.2 | Environmental protections and recovery alternatives | Workloads, Continuous Validation |
| A1.3 | Recovery plan testing and documentation | Runbooks, Compliance Assessment |

### ISO 27001:2022 Controls Addressed

| Control | Description | R3VP Feature |
|---|---|---|
| A 8.13 | Information backup | Workloads, RPO tracking |
| A 8.14 | Redundancy of information processing facilities | Test Runs, RTO measurement |
| A 5.30 | ICT readiness for business continuity | Compliance Frameworks, Scorecard |

### DORA Articles Addressed

| Article | Description | R3VP Feature |
|---|---|---|
| Art. 11 | Backup policies and restoration procedures | Test Runs, Evidence Vault |
| Art. 12 | Recovery time and recovery point objectives | RTO/RPO tracking, Compliance |
| Art. 17 | Testing of digital operational resilience | Test Runs, Schedules, Reports |

---

## Appendix B - Glossary

| Term | Definition |
|---|---|
| age | A modern file encryption tool used to encrypt the credential vault on the appliance. |
| Appliance | The on-premises Python process that holds credentials and executes validation workflows. |
| Evidence Bundle | A ZIP archive containing logs, screenshots, and metadata from a test run, signed with SHA-256. |
| mTLS | Mutual TLS. Both the client (appliance) and server (API) present certificates for authentication. |
| RTO | Recovery Time Objective. The maximum acceptable time to restore a workload after an incident. |
| RPO | Recovery Point Objective. The maximum acceptable age of the most recent backup at the time of recovery. |
| SOPS | Secrets OPerationS. A tool for encrypting configuration files using various key providers. |
| Temporal.io | A workflow orchestration platform used to execute and monitor multi-step validation workflows. |
| IOC | Indicator of Compromise. File hashes, extensions, or behaviors associated with known malware or ransomware. |
| MSSP | Managed Security Service Provider. A partner organization that delivers security services to multiple customers. |
| Readiness Score | A 0-100 composite metric reflecting the overall validated recovery capability of an organization. |
| Micro-check | A lightweight, rapid validation check run every 15 minutes as part of Continuous Validation. |

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy | https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
