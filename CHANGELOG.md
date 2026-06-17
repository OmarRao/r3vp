# Changelog

All notable changes to R3VP are documented here.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## [Unreleased] - Phase 6: Extended Hypervisors and Google Cloud

### Added
- Proxmox VE connector: proxmoxer REST API, PBS backup integration, snapshot create/restore
- Nutanix AHV connector: Prism Central v3 REST API, recovery point management
- RHV / oVirt connector: oVirt Engine Python SDK, snapshot preview and commit
- XenServer / Citrix Hypervisor connector: XenAPI XML-RPC, VM clone from snapshot
- Sangfor HCI connector: vendor REST API, token auth, snapshot restore
- GCP Backup connector: google-cloud-compute, Application Default Credentials, instance restore from snapshot
- Provider routing in Temporal activities extended from 4 to 10 providers
- Workload model: provider_cluster field for cluster/pool/zone metadata
- Alembic migration 0007 for provider_cluster column
- Portal /dashboard/providers: 10-provider card grid, extended hypervisor support matrix
- Portal dashboard: 10-provider coverage widget
- R3VP_PROVIDER env var now accepts: vmware, hyperv, azure, aws, proxmox, nutanix, rhv, xenserver, sangfor, gcp
- New pyproject.toml dependencies: proxmoxer>=2.0, google-cloud-compute>=1.14, google-auth>=2.28

---

## [0.5.0] - Phase 5 - 2026-06-17

### Added
- Veeam B&R 13.0.2 support: API version v1.2 with auto-detection via serverInfo
- Veeam 13 backup repositories endpoint: list repos with capacity and free space
- Veeam 13 malware detection events: ingest Veeam inline scanner findings
- Veeam 13 instant recovery path update: /instantRecovery/vm (v1.2) vs /instantRecovery/vmware/vm (v1.1)
- Veeam backup job control: trigger immediate backup jobs, monitor session progress
- Hyper-V connector: WMI-based VM inventory, checkpoint management, isolated virtual switch
- AWS Backup connector: vault inventory, EC2 recovery points, test restore to isolated VPC subnet, EC2 health checks
- Azure Backup connector: Recovery Services Vault integration, protected VM list, restore to isolated resource group
- Multi-cloud workflow routing: Temporal activities dispatch to correct connector based on configured provider
- Provider breakdown dashboard: per-provider workload count, pass rate, avg RTO
- /dashboard/providers page: detailed provider coverage cards with pass rate bar charts
- Provider filter on workload list
- Workload model: provider, cloud_resource_id, cloud_region fields
- Alembic migration 0006: workload provider columns
- Multi-cloud readiness API: GET /v1/multicloud/provider-summary, GET /v1/multicloud/workloads
- New dependencies: boto3, azure-identity, azure-mgmt-recoveryservicesbackup, msal

---

## [0.4.0] - Phase 4 - 2026-06-16

### Added
- Ransomware, malware, APT, and vulnerability signature database with automatic cloud sync
- File system and process scanner that cross-references running processes against the threat DB
- YARA rules engine: load and execute custom or community YARA rules against scanned artifacts
- SOAR integration: Splunk SOAR and Palo Alto XSOAR webhook triggers on threat detection
- SIEM integration: CEF/Syslog output for Splunk, IBM QRadar, and Microsoft Sentinel
- Automated incident response API: triggers an immediate Veeam backup and creates a SecOps workflow on threat detection
- VeeamONE reporting integration: pushes threat and recovery events to VeeamONE dashboards
- Threat scanner portal pages: scan dashboard, findings detail, active incidents
- Console notification pane: real-time threat alerts shown in portal without page refresh
- Email notifications for incident alerts (SES)

---

## [0.3.0] - Phase 3 - 2026-06-15

### Added
- SLA breach notifications: email (SES), Slack incoming webhook, Teams adaptive card webhook
- Notification channel management: POST/GET/DELETE /v1/notifications, scoped by org
- Portal settings page: org info, notification channels, default RTO/RPO targets
- Audit log CSV export: GET /v1/audit-log/export with 90-day date range
- Appliances list and detail pages in portal: status badges (active/stale/offline based on heartbeat)
- Role-based access control: admin and viewer roles, write endpoints protected with AdminUser dependency
- User provisioning endpoint: POST /v1/users/provision for role assignment
- Production Terraform: ECS Fargate auto-scaling (1-4 tasks), ALB with TLS 1.3, CloudFront CDN
- Cyber insurance evidence report: NIST CSF Recover function mapping, PDF attestation document
- Integration test suite: real Postgres tests for inventory sync upsert and readiness score calculation
- Portal-facing appliances API: GET/DELETE /v1/portal/appliances with workload counts
- Appliance deregister capability

### Changed
- finalise_run() now dispatches breach notifications as a best-effort post-commit step
- trigger_test_run, set_targets, set_schedule now require admin role

---

## [0.2.0] - Phase 2 - 2026-06-14

### Added
- Temporal workflow trigger wired into the API: trigger_test_run enqueues RecoveryTestWorkflow
- Temporal lifespan in FastAPI: connects on startup, graceful shutdown on exit
- Full inventory sync: sync_inventory activity posts explicit field mapping to relay client
- Portal workload detail page: stats, RTO/RPO targets form, test run history, Run Test Now
- Live test run progress view: 5-second polling while status is running/pending, step timeline
- PDF evidence report: Jinja2 HTML template rendered via WeasyPrint, full step/health check data
- Scheduled test runs: schedule_cron field on workloads, APScheduler loads and fires cron jobs
- Veeam version auto-detection: reads /api/v1/serverInfo on startup, routes to correct API path
- On-premises install script (bash): Docker check, cert generation, secrets template
- Windows PowerShell install script: same flow for Windows environments
- Appliance OVA packaging: Packer HCL2 template, configure-from-ovf.sh reads vSphere OVF properties

### Changed
- Restore point list routes to correct API path for Veeam v1.0 vs v1.1
- Instant recovery raises NotImplementedError on Veeam 10 (no API support)

---

## [0.1.0] - Phase 1 - 2026-06-13

### Added
- Python 3.12 monorepo with uv workspace (apps/appliance, apps/api, apps/portal)
- Lightweight appliance: outbound-only mTLS relay client, SOPS+age credential vault
- Veeam B&R REST API connector: token auth, auto-refresh, list jobs/VMs/restore points, instant recovery
- VMware vCenter connector: pyVmomi, isolated VLAN provisioning, VMware Tools polling, screenshot
- Temporal workflow: RecoveryTestWorkflow with 10 activities and saga teardown pattern
- Health checks: Windows OS (WinRM), Linux OS (SSH + systemctl), Active Directory LDAP, SQL Server stubs
- FastAPI SaaS backend: appliance relay, workload inventory, test run management, readiness scoring
- Auth0 JWT authentication with JWKS RS256 verification and org_id claim extraction
- PostgreSQL 16 schema: orgs, appliances, workloads, test_runs, test_run_steps, health_check_results, audit_events
- Alembic migrations (0001 initial)
- Next.js 14 portal: Auth0 login, dashboard with readiness gauge, RTO/RPO chart, workload grid
- mTLS client certificate verification: thumbprint checked against DB on every appliance request
- GitHub Actions CI: lint, typecheck, unit tests, integration tests, Docker builds
- Terraform modules: RDS PostgreSQL 16, S3 evidence bucket with KMS encryption
- mTLS cert generation scripts (bash + PowerShell)
- Architecture Decision Records: appliance runtime, Temporal workflow engine

---

## Roadmap

### Phase 5 (planned): Multi-cloud and Hyper-V support
- Hyper-V connector: WMI-based VM inventory and Hyper-V checkpoint recovery
- Azure Blob Storage backup connector
- AWS Backup connector
- Multi-cloud workload dashboard with provider breakdown

### Phase 6 (planned): Compliance frameworks and advanced reporting
- SOC 2 Type II evidence package generator
- ISO 27001 Annex A mapping
- CIS Controls v8 mapping
- Executive summary email digest (weekly/monthly)
- API-first reporting: programmatic evidence export for GRC tools
