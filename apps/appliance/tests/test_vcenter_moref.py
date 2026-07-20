"""Unit tests for pure vCenter moref-resolution planning.

Exercises identity extraction from recorded Veeam session bodies and the ordered
lookup plan, without importing pyVmomi or touching a live vCenter.

Built by Omar Rao.
"""
import json
from pathlib import Path

from src.connectors.vcenter.moref import (
    MorefLookupMethod,
    RecoveredVmIdentity,
    parse_recovered_vm_identity,
)

FIXTURES = Path(__file__).parent / "fixtures" / "veeam"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_parse_identity_from_working_session():
    identity = parse_recovered_vm_identity(load("session_working.json"))
    assert identity.instance_uuid == "5029d1b2-3c4a-5e6f-7081-92a3b4c5d6e7"
    assert identity.bios_uuid == "42301a2b-3c4d-5e6f-7081-92a3b4c5d6e7"
    assert identity.dns_name == "web-01.corp.local"
    assert identity.vm_name == "web-01"


def test_lookup_plan_prefers_instance_uuid_first():
    identity = parse_recovered_vm_identity(load("session_working.json"))
    plan = identity.lookup_plan()
    methods = [m for m, _ in plan]
    assert methods == [
        MorefLookupMethod.INSTANCE_UUID,
        MorefLookupMethod.BIOS_UUID,
        MorefLookupMethod.DNS_NAME,
        MorefLookupMethod.VM_NAME,
    ]
    assert plan[0][1] == "5029d1b2-3c4a-5e6f-7081-92a3b4c5d6e7"


def test_parse_identity_no_restored_object_is_empty():
    identity = parse_recovered_vm_identity(load("session_starting.json"))
    assert identity.lookup_plan() == []


def test_lookup_plan_skips_missing_fields():
    identity = RecoveredVmIdentity(bios_uuid="abc", vm_name="only-name")
    methods = [m for m, _ in identity.lookup_plan()]
    assert methods == [MorefLookupMethod.BIOS_UUID, MorefLookupMethod.VM_NAME]


def test_parse_identity_alternate_result_key():
    body = {"result": {"virtualMachine": {"name": "db-02", "uuid": "u-1"}}}
    identity = parse_recovered_vm_identity(body)
    assert identity.vm_name == "db-02"
    assert identity.bios_uuid == "u-1"
