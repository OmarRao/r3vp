"""Appliance entry point: loads secrets from vault, starts Temporal worker."""
import asyncio
import argparse
import structlog

from src.vault.loader import load_secrets_into_settings
from src.relay.client import RelayClient
from src.workers.runner import run_worker

log = structlog.get_logger()


async def _run(dev: bool) -> None:
    log.info("r3vp appliance starting", dev=dev)
    await load_secrets_into_settings()
    relay = RelayClient()
    await relay.register()
    log.info("appliance registered with SaaS platform")
    await run_worker()


def main() -> None:
    parser = argparse.ArgumentParser(description="R3VP Validation Appliance")
    parser.add_argument("--dev", action="store_true", help="Dev mode (skip cert pinning)")
    args = parser.parse_args()
    asyncio.run(_run(dev=args.dev))


if __name__ == "__main__":
    main()
