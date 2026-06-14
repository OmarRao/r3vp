"""Base class for all health check plugins."""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseHealthCheck(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, vm_moref: str) -> dict:
        """Run the health check. Returns {"passed": bool, "output": str}."""
        ...
