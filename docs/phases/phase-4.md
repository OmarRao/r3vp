# Phase 4: Threat Intelligence and Incident Response

**Status:** In Progress

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/

## Overview

Phase 4 transforms R3VP from a recovery validation platform into a full threat-aware resilience platform. It adds a threat intelligence engine that scans the environment for ransomware, malware, APT indicators, and known vulnerabilities, then automatically triggers incident response workflows when threats are detected.

## Threat Signature Database

A SQLite database on the appliance, synced from the R3VP cloud threat intelligence feed. Contains:

- **Ransomware signatures**: file hashes, process names, registry keys, network IOCs for known ransomware families (LockBit, BlackCat/ALPHV, Cl0p, Royal, Black Basta, and others)
- **Malware signatures**: file hashes and behavioral indicators for common malware families
- **APT indicators**: IP addresses, domains, file hashes, and TTPs associated with tracked APT groups (aligned to MITRE ATT&CK)
- **CVE vulnerability database**: critical and high-severity CVEs relevant to Veeam, VMware, Windows Server, and common server software
- **YARA rules**: community and R3VP-authored YARA rules for detection

The database syncs automatically on a configurable schedule (default: every 6 hours). Signatures include severity ratings, MITRE ATT&CK technique mappings, and recommended remediation steps.

## Scanner

The appliance scans:

- **Running processes**: cross-references process names and paths against the threat DB
- **File system**: scans configured paths for file hashes matching known malware
- **Network connections**: checks active connections against malicious IP/domain lists
- **Registry** (Windows): checks run keys and common persistence locations
- **Backup infrastructure**: specifically checks Veeam processes, services, and configuration for signs of tampering

Scans run on a schedule (default: every hour) and on-demand via the portal or API.

## YARA Rules Engine

YARA rules ship with the threat DB. The scanner applies them to:
- New files written to monitored paths
- Memory dumps of suspicious processes
- Log files from Veeam and the OS

Custom YARA rules can be uploaded via the portal. Rules are validated before activation.

## SOAR Integration

When a threat is confirmed (severity >= HIGH or any ransomware signature matched):

- Sends a structured alert to configured SOAR platforms:
  - **Splunk SOAR (Phantom)**: REST API event creation with full IOC context
  - **Palo Alto XSOAR (Cortex)**: incident creation via REST API
  - **Generic webhook**: JSON payload compatible with most SOAR platforms
- Alert payload includes: threat name, severity, affected host, IOCs, MITRE ATT&CK technique, recommended playbook

## SIEM Integration

All scan events, threat detections, and incident response actions emit structured log records:

- **CEF (Common Event Format)**: compatible with Splunk, ArcSight, QRadar
- **LEEF**: IBM QRadar native format
- **JSON over Syslog**: Microsoft Sentinel, Elastic SIEM

Events follow the standard schema: timestamp, severity, event type, source host, affected resource, threat name, IOCs.

## Incident Response API

On threat detection, the platform automatically:

1. Triggers an immediate Veeam backup of affected VMs (pre-incident clean restore point)
2. Creates a SecOps workflow in the portal with the full threat context
3. Sends notifications to configured channels (console, email, Slack, Teams)
4. Dispatches to configured SOAR platform
5. Emits SIEM events
6. Reports to VeeamONE

The incident response can also be triggered manually via the portal or API.

## VeeamONE Integration

R3VP pushes events to VeeamONE via the VeeamONE REST API:
- Recovery test results: passed/failed, actual RTO/RPO vs targets
- Threat detection events: threat name, severity, affected VMs
- Incident response actions: backup triggered, workflow created

VeeamONE dashboards show R3VP readiness scores and threat status alongside Veeam infrastructure metrics.

## Console Notifications

The portal shows real-time threat alerts in a notification pane without requiring a page refresh. A persistent connection (server-sent events) delivers new scan findings and incident updates as they occur.

## Portal Pages

- **Threat Scanner**: scan status, last scan time, finding summary by severity, scan history
- **Findings**: table of all detected threats, filterable by severity/type/status, with dismiss and investigate actions
- **Incidents**: active and resolved incidents, SecOps workflow status, SOAR/SIEM dispatch status
- **Threat Config**: SOAR webhook config, SIEM output config, VeeamONE config, scan schedule, YARA rule upload
