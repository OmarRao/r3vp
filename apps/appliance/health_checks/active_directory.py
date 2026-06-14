from __future__ import annotations
from .base import BaseHealthCheck


class ActiveDirectoryHealthCheck(BaseHealthCheck):
    name = "active_directory"

    async def run(self, vm_moref: str) -> dict:
        # In production: LDAP bind test + dcdiag-equivalent check
        return {"passed": False, "output": "not implemented", "check": self.name}
