"""Pure helpers for resolving a recovered VM's vCenter moref.

The live moref lookup uses pyVmomi's SearchIndex, but *deciding what to look up*
(instance UUID vs BIOS UUID vs DNS name, and in what order) is pure logic driven
by the Veeam instant-recovery session's restored-object reference. Extracting it
here keeps it unit-testable without pyVmomi or a live vCenter.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MorefLookupMethod(str, Enum):
    INSTANCE_UUID = "instance_uuid"   # SearchIndex.FindByUuid(..., instanceUuid=True)
    BIOS_UUID = "bios_uuid"           # SearchIndex.FindByUuid(..., instanceUuid=False)
    DNS_NAME = "dns_name"             # SearchIndex.FindByDnsName
    VM_NAME = "vm_name"               # container-view scan by name (last resort)


@dataclass(frozen=True)
class RecoveredVmIdentity:
    instance_uuid: str | None = None
    bios_uuid: str | None = None
    dns_name: str | None = None
    vm_name: str | None = None

    def lookup_plan(self) -> list[tuple[MorefLookupMethod, str]]:
        """Ordered (method, value) pairs to try, most reliable first.

        Instance UUID is globally unique per vCenter and survives a rename, so it
        is preferred. BIOS UUID can collide across clones, DNS name needs guest
        networking up, and name matching is the final fallback.
        """
        plan: list[tuple[MorefLookupMethod, str]] = []
        if self.instance_uuid:
            plan.append((MorefLookupMethod.INSTANCE_UUID, self.instance_uuid))
        if self.bios_uuid:
            plan.append((MorefLookupMethod.BIOS_UUID, self.bios_uuid))
        if self.dns_name:
            plan.append((MorefLookupMethod.DNS_NAME, self.dns_name))
        if self.vm_name:
            plan.append((MorefLookupMethod.VM_NAME, self.vm_name))
        return plan


def parse_recovered_vm_identity(session_body: dict) -> RecoveredVmIdentity:
    """Extract VM identifiers from a Veeam instant-recovery session body.

    Veeam's session payload nests the restored object under a few possible keys
    depending on version; we look through the known shapes and pull whatever
    identifiers are present. Missing fields simply stay ``None`` so the caller's
    lookup plan degrades gracefully.

    NOTE: the exact key names below are drawn from ADR-003 and the Veeam REST
    schema and MUST be confirmed against a recorded live session response
    (see the real-lab verification boundary in the PR).
    """
    obj = (
        session_body.get("restoredObject")
        or session_body.get("recoveredObject")
        or session_body.get("result")
        or {}
    )
    if isinstance(obj, dict):
        vm = obj.get("vm") or obj.get("virtualMachine") or obj
    else:
        vm = {}

    # Only the restored-object subtree is searched; the top-level session body
    # carries the *session* name, which must not be mistaken for a VM name.
    def pick(*keys: str) -> str | None:
        for src in (vm, obj):
            if not isinstance(src, dict):
                continue
            for key in keys:
                val = src.get(key)
                if val:
                    return str(val)
        return None

    return RecoveredVmIdentity(
        instance_uuid=pick("instanceUuid", "instanceUUID", "vmInstanceUuid"),
        bios_uuid=pick("biosUuid", "biosUUID", "uuid", "vmUuid"),
        dns_name=pick("dnsName", "hostName", "fqdn"),
        vm_name=pick("name", "vmName", "displayName"),
    )
