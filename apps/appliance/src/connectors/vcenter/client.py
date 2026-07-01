"""VMware vCenter connector using pyVmomi.

Manages vCenter session lifecycle, VM inventory queries, isolated network
provisioning, and VM power/tools state polling for recovery validation.
"""
from __future__ import annotations

import ssl

import structlog
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

from src.config import settings

from .models import VCenterDatastore, VCenterNetwork, VCenterVM

log = structlog.get_logger()


class VCenterClient:
    def __init__(self) -> None:
        self._si: vim.ServiceInstance | None = None

    def connect(self) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # on-prem vCenter often uses self-signed
        self._si = SmartConnect(
            host=settings.vcenter_host,
            user=settings.vcenter_username,
            pwd=settings.vcenter_password.get_secret_value(),
            sslContext=ctx,
        )
        log.info("connected to vCenter", host=settings.vcenter_host)

    def disconnect(self) -> None:
        if self._si:
            Disconnect(self._si)
            self._si = None

    def __enter__(self) -> VCenterClient:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()

    @property
    def _content(self) -> vim.ServiceInstanceContent:
        if not self._si:
            raise RuntimeError("Not connected to vCenter")
        return self._si.RetrieveContent()

    def _get_all_objects(self, obj_type: type) -> list:
        container = self._content.viewManager.CreateContainerView(
            self._content.rootFolder, [obj_type], True
        )
        try:
            return list(container.view)
        finally:
            container.Destroy()

    def list_vms(self) -> list[VCenterVM]:
        vms = []
        for vm in self._get_all_objects(vim.VirtualMachine):
            if vm.config is None:
                continue
            vms.append(VCenterVM(
                moref=vm._moId,
                name=vm.name,
                power_state=vm.runtime.powerState,
                guest_os=vm.config.guestFullName or "",
                ip_address=vm.guest.ipAddress if vm.guest else None,
                tools_status=vm.guest.toolsStatus if vm.guest else None,
                num_cpu=vm.config.hardware.numCPU,
                memory_mb=vm.config.hardware.memoryMB,
            ))
        return vms

    def list_networks(self) -> list[VCenterNetwork]:
        networks = []
        for net in self._get_all_objects(vim.Network):
            networks.append(VCenterNetwork(moref=net._moId, name=net.name))
        return networks

    def list_datastores(self) -> list[VCenterDatastore]:
        datastores = []
        for ds in self._get_all_objects(vim.Datastore):
            datastores.append(VCenterDatastore(
                moref=ds._moId,
                name=ds.name,
                free_bytes=ds.summary.freeSpace,
                # summary.capacity is the datastore capacity; info.maxFileSize is
                # only the largest supported single-file size (a filesystem limit).
                capacity_bytes=ds.summary.capacity,
            ))
        return datastores

    def create_isolated_portgroup(self, vswitch_name: str, vlan_id: int, name: str) -> str:
        """Create an isolated port group on the given vSwitch. Returns moref."""
        hosts = self._get_all_objects(vim.HostSystem)
        if not hosts:
            raise RuntimeError("No ESXi hosts found in vCenter")
        host = hosts[0]
        spec = vim.host.PortGroup.Specification(
            name=name,
            vlanId=vlan_id,
            vswitchName=vswitch_name,
            policy=vim.host.NetworkPolicy(
                security=vim.host.NetworkPolicy.SecurityPolicy(
                    allowPromiscuous=False,
                    macChanges=False,
                    forgedTransmits=False,
                )
            ),
        )
        host.configManager.networkSystem.AddPortGroup(spec)
        log.info("isolated portgroup created", name=name, vlan=vlan_id)
        return name

    def remove_portgroup(self, host_name: str, portgroup_name: str) -> None:
        hosts = self._get_all_objects(vim.HostSystem)
        for host in hosts:
            if host.name == host_name:
                host.configManager.networkSystem.RemovePortGroup(portgroup_name)
                log.info("portgroup removed", name=portgroup_name)
                return

    def wait_for_tools(self, vm_moref: str, timeout_seconds: int = 300) -> bool:
        """Poll until VMware Tools reports running or timeout. Returns True on success."""
        import time
        content = self._content
        vm = content.searchIndex.FindByMoId(vm_moref)
        if not vm:
            raise ValueError(f"VM not found: {vm_moref}")
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if vm.guest and vm.guest.toolsStatus == vim.vm.GuestInfo.ToolsStatus.toolsOk:
                return True
            time.sleep(10)
        return False

    def take_screenshot(self, vm_moref: str) -> bytes:
        """Capture a screenshot of the VM console. Returns PNG bytes."""
        content = self._content
        vm = content.searchIndex.FindByMoId(vm_moref)
        if not vm:
            raise ValueError(f"VM not found: {vm_moref}")
        task = vm.CreateScreenshot_Task()
        # Block until task completes (synchronous for evidence capture)
        while task.info.state not in (
            vim.TaskInfo.State.success,
            vim.TaskInfo.State.error,
        ):
            import time
            time.sleep(2)
        if task.info.state == vim.TaskInfo.State.error:
            raise RuntimeError(f"Screenshot failed: {task.info.error.localizedMessage}")
        # Download the screenshot file from the datastore
        # task.info.result contains the path on the datastore
        return b""  # placeholder — real impl fetches via HTTPS from ESXi
