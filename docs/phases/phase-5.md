# Phase 5: Multi-Cloud and Hyper-V Support

**Status:** In Progress

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/

## Overview

Phase 5 expands R3VP from a VMware-only platform into a true multi-cloud and multi-hypervisor readiness platform. Recovery validation tests now run against workloads protected by Hyper-V, Azure Backup, and AWS Backup in addition to the existing VMware vSphere and Veeam B&R flow.

This phase also upgrades the Veeam connector to fully support Veeam B&R 13.0.2, taking advantage of the new v1.2 API including inline malware detection event ingestion.

## Veeam B&R 13.0.2

Veeam 13 introduces API version v1.2. R3VP auto-detects the Veeam build version at startup via the /api/v1/serverInfo endpoint and routes all API calls to the correct path.

Key v1.2 additions surfaced in R3VP:

**Backup repositories**: GET /backupRepositories lists all configured repositories with capacity and free space. R3VP displays repository health in the appliance detail page.

**Instant recovery path**: The instant recovery endpoint moved from /instantRecovery/vmware/vm to /instantRecovery/vm in v1.2. R3VP routes to the correct path automatically.

**Malware detection events**: Veeam 13 ships with built-in inline ransomware detection. GET /malwareDetection/events returns events from Veeam's own scanner. R3VP ingests these events and correlates them with its own threat scanner findings, giving a unified threat view combining R3VP's YARA/signature scanning and Veeam's inline detection.

**Backup job control**: POST /jobs/{jobId}/start triggers an immediate backup job. R3VP uses this for the pre-incident backup step in incident response workflows, replacing the previous stub implementation.

**Job session monitoring**: GET /jobSessions/{sessionId} tracks backup job progress. R3VP monitors the session until the backup completes before confirming the clean restore point is saved.

## Hyper-V Connector

The Hyper-V connector uses Windows Management Instrumentation (WMI) via pywin32 to interact with a local or remote Hyper-V host.

**VM inventory**: Lists all VMs with state (Running, Off, Saved, Paused), CPU count, memory, and generation.

**Checkpoint management**: Creates production checkpoints before test recovery. Restores VMs to checkpoint state for the recovery test. Deletes test checkpoints during teardown.

**Isolated virtual switch**: Creates a new Internal virtual switch for the test network. The restored VM is connected to this switch during the health check phase, preventing any network contact with production systems. The switch is deleted at teardown.

**Health checks**: Reads VM health state and operational status from WMI after recovery. Combined with WinRM OS health checks from the existing health check module.

Hyper-V support requires the appliance to be running on a Windows host with the Hyper-V role installed. It is not available on Linux-based appliances.

## Azure Backup Connector

The Azure Backup connector uses the Azure SDK (azure-identity + azure-mgmt-recoveryservicesbackup) to integrate with Recovery Services Vaults.

**Authentication**: Uses DefaultAzureCredential which tries managed identity first, then environment variables, then Azure CLI. For on-premises appliances, a service principal (client ID + secret in the SOPS vault) is used.

**Protected VM inventory**: Lists all VMs protected by a Recovery Services Vault with their last backup time and health status.

**Recovery point listing**: Lists all recovery points for a protected VM, sorted by time.

**Test restore**: Restores a VM to an isolated resource group with a dedicated isolated VNet. The target resource group has no peering to production networks and no public IP assignments. R3VP monitors the Azure Backup restore job until completion.

**Health check**: Reads VM status via Azure Instance Metadata Service after restore, combined with WinRM/SSH checks from the existing health check module.

## AWS Backup Connector

The AWS Backup connector uses boto3 with the default credential chain (IAM instance profile, environment variables, or ~/.aws/credentials).

**Vault inventory**: Lists all AWS Backup vaults in the configured region with recovery point counts.

**Recovery point listing**: Lists recovery points per vault, filtered by resource type (EC2, RDS, EFS).

**Test restore**: Starts a restore job to an isolated VPC subnet with no internet gateway or NAT. R3VP monitors the restore job ID until the EC2 instance is running.

**Health check**: Reads EC2 instance status checks (instance and system) via describe_instance_status. Combined with SSM Run Command for OS-level health checks.

**Teardown**: Terminates the restored EC2 instance after the test completes.

## Multi-Cloud Portal

The portal gains a new Provider Coverage section on the main dashboard and a dedicated /dashboard/providers page.

The provider breakdown shows per-provider: workload count, recovery test count, pass rate (color-coded green/yellow/red), and average actual RTO. Every provider is shown even if not yet configured, prompting the operator to connect it.

The workload list page gains a provider filter dropdown so operators can view and manage workloads per cloud platform.

## Version Support Matrix

| Veeam Version | API Version | Instant Recovery | Malware Events | Backup Repos |
|---|---|---|---|---|
| Veeam 10.x | v1.0 | Not supported | No | No |
| Veeam 11.x | v1.0 | Supported | No | No |
| Veeam 12.x | v1.1 | Supported | No | No |
| Veeam 13.0.2+ | v1.2 | Supported | Yes | Yes |
