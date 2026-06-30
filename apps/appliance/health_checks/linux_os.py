from __future__ import annotations

import asyncio

from .base import BaseHealthCheck


class LinuxOSHealthCheck(BaseHealthCheck):
    name = "linux_os_boot"

    async def run(self, vm_moref: str) -> dict:
        # In production: SSH to the recovered VM's IP, run `hostname && systemctl is-system-running`
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                "root@placeholder", "systemctl is-system-running",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode().strip()
            passed = output in ("running", "degraded")
            return {"passed": passed, "output": output, "check": self.name}
        except Exception as exc:
            return {"passed": False, "output": str(exc), "check": self.name}
