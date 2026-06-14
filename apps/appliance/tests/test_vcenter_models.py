"""Unit tests for vCenter connector models — no network required."""
from src.connectors.vcenter.models import VCenterVM, VCenterNetwork, VCenterDatastore


def test_vcenter_vm_optional_fields() -> None:
    vm = VCenterVM(moref="vm-100", name="dc-01", power_state="poweredOn", guest_os="Windows Server 2022")
    assert vm.ip_address is None
    assert vm.tools_status is None


def test_vcenter_datastore_defaults() -> None:
    ds = VCenterDatastore(moref="ds-1", name="datastore1")
    assert ds.free_bytes == 0
    assert ds.capacity_bytes == 0
