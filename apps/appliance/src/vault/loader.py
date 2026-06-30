"""Decrypt SOPS-encrypted secrets file and populate settings at runtime.

Secrets are encrypted with age using a customer-managed key that never
leaves the customer environment. The plaintext is held only in memory.
"""
import subprocess

import yaml
from pydantic import SecretStr

from src.config import settings


async def load_secrets_into_settings() -> None:
    plaintext = _decrypt_sops(settings.vault_secrets_path, settings.vault_age_key_path)
    data = yaml.safe_load(plaintext)

    veeam = data.get("veeam", {})
    settings.veeam_base_url = veeam.get("base_url", "")
    settings.veeam_username = veeam.get("username", "")
    settings.veeam_password = SecretStr(veeam.get("password", ""))

    vcenter = data.get("vcenter", {})
    settings.vcenter_host = vcenter.get("host", "")
    settings.vcenter_username = vcenter.get("username", "")
    settings.vcenter_password = SecretStr(vcenter.get("password", ""))


def _decrypt_sops(secrets_path: str, key_path: str) -> str:
    result = subprocess.run(
        ["sops", "--decrypt", secrets_path],
        capture_output=True,
        text=True,
        env={"SOPS_AGE_KEY_FILE": key_path},
        check=True,
    )
    return result.stdout
