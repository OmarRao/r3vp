from __future__ import annotations

import asyncio

from .base import BaseHealthCheck


class WindowsOSHealthCheck(BaseHealthCheck):
    name = "windows_os_boot"

    async def run(self, vm_moref: str) -> dict:
        # In production: WinRM ping to the recovered VM's IP address
        # Verifies that Windows is booted, responding, and RDP/WinRM is live
        try:
            proc = await asyncio.create_subprocess_exec(
                "winrs", "-r:placeholder", "hostname",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            passed = proc.returncode == 0
            return {"passed": passed, "output": stdout.decode().strip(), "check": self.name}
        except Exception as exc:
            return {"passed": False, "output": str(exc), "check": self.name}
