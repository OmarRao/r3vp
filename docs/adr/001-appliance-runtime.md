# ADR-001: Appliance Runtime — Python

**Status:** Accepted
**Date:** 2026-06-14

## Context
The appliance must connect to Veeam B&R and VMware vCenter APIs, run health checks over WinRM/SSH, and communicate with Temporal Cloud. Language choice affects SDK availability, packaging complexity, and team ramp-up.

## Decision
Python 3.12 with `uv` for dependency management.

## Rationale
- `pyVmomi` is the only first-class VMware vSphere SDK available
- Veeam has a REST API (language-agnostic) but Python has the best HTTP client ecosystem for async retries and mTLS (`httpx`)
- `temporalio` SDK is mature and well-tested
- `paramiko` / `pywinrm` for SSH/WinRM health checks
- Consistent language with the API backend reduces cognitive overhead

## Consequences
- OVA packaging uses Ubuntu + Docker + Python — straightforward
- Team needs Python expertise; no Go/Rust runtime performance concerns at this scale
