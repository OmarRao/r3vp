# Phase 2: Workflow Wiring and Portal Pages

**Status:** Complete
**Release:** v0.2.0 (2026-06-14)

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/

## What was built

Phase 2 connected the Phase 1 components end-to-end and added the user-facing portal pages needed to actually operate R3VP.

## Temporal workflow trigger

The API now enqueues a Temporal workflow when a test run is triggered. The lifespan context connects to Temporal Cloud on startup with optional mTLS. If Temporal is unavailable, the run stays in pending state and the appliance polls for it via the commands endpoint.

## Inventory sync

The sync_inventory Temporal activity now posts the complete workload list to the relay client after discovering VMs from Veeam. The API upserts workloads using a partial unique index on (appliance_id, veeam_object_id) so re-syncing never creates duplicates.

## Veeam version compatibility

The appliance detects the Veeam build version at startup by calling /api/v1/serverInfo. It routes restore point queries to the correct API path for v1.0 (Veeam 11) vs v1.1 (Veeam 12+). Instant recovery raises a clear error on Veeam 10 which does not support it via API.

## Portal pages

**Workload detail** shows VM stats, editable RTO/RPO targets, test run history table, and a Run Test Now button that redirects to the test run detail page on success.

**Test run detail** polls every 5 seconds while the run is active. Shows the workflow step timeline with status icons, live elapsed time indicator, and a PDF report download link.

## PDF evidence report

WeasyPrint renders a Jinja2 HTML template to PDF. The report includes RTO/RPO metrics, workflow step timeline, health check results, and Omar Rao attribution in the footer. Returned as application/pdf with Content-Disposition header for direct download.

## Scheduled test runs

APScheduler loads workload cron schedules from the database on startup and fires Temporal workflows on schedule. A new PUT /v1/workloads/{id}/schedule endpoint saves the cron expression. Alembic migration 0002 adds the schedule_cron column.

## Install scripts

Bash and PowerShell scripts automate the on-premises appliance setup: Docker check, directory creation, cert generation, and secrets template setup.

## OVA packaging

A Packer HCL2 template builds an Ubuntu 22.04 OVA with Docker, sops, and age pre-installed. configure-from-ovf.sh reads vSphere OVF properties at boot and writes /opt/r3vp/.env automatically. The OVA requires no post-deploy configuration except encrypting the credentials vault.
