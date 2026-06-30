"""Outbound-only mTLS relay client: all SaaS communication goes through here.

The appliance never opens inbound ports. Requests are outbound HTTPS with
mutual TLS — the appliance presents its client cert, the SaaS platform
verifies it against the registered thumbprint.
"""
import ssl

import httpx
import structlog

from src.config import settings

log = structlog.get_logger()


def _build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cafile=settings.mtls_ca_path)
    ctx.load_cert_chain(certfile=settings.mtls_cert_path, keyfile=settings.mtls_key_path)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    return ctx


class RelayClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.saas_base_url,
            verify=_build_ssl_context(),
            timeout=30.0,
            headers={
                "X-Appliance-ID": settings.appliance_id,
                "X-Org-ID": settings.org_id,
            },
        )

    async def register(self) -> None:
        resp = await self._client.post(
            "/v1/appliance/register",
            json={"appliance_id": settings.appliance_id, "org_id": settings.org_id},
        )
        resp.raise_for_status()
        log.info("appliance registered", appliance_id=settings.appliance_id)

    async def heartbeat(self) -> None:
        resp = await self._client.post(
            "/v1/appliance/heartbeat",
            json={"appliance_id": settings.appliance_id, "version": "0.1.0"},
        )
        resp.raise_for_status()

    async def sync_inventory(self, payload: dict) -> None:
        resp = await self._client.post("/v1/appliance/inventory/sync", json=payload)
        resp.raise_for_status()

    async def post_progress(self, run_id: str, step: dict) -> None:
        resp = await self._client.post(f"/v1/appliance/test-runs/{run_id}/progress", json=step)
        resp.raise_for_status()

    async def post_result(self, run_id: str, result: dict) -> None:
        resp = await self._client.post(f"/v1/appliance/test-runs/{run_id}/result", json=result)
        resp.raise_for_status()

    async def upload_evidence(self, run_id: str, filename: str, data: bytes) -> None:
        resp = await self._client.post(
            f"/v1/appliance/test-runs/{run_id}/evidence",
            files={"file": (filename, data, "application/octet-stream")},
        )
        resp.raise_for_status()

    async def get_pending_commands(self) -> list[dict]:
        resp = await self._client.get("/v1/appliance/commands")
        resp.raise_for_status()
        return resp.json().get("commands", [])

    async def close(self) -> None:
        await self._client.aclose()
