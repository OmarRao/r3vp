from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class ApplianceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="R3VP_", env_file=".env")

    appliance_id: str
    org_id: str
    saas_base_url: str = "https://api.r3vp.io"

    # mTLS — paths to certs on disk (private key never leaves appliance)
    mtls_cert_path: str = "/certs/appliance.crt"
    mtls_key_path: str = "/certs/appliance.key"
    mtls_ca_path: str = "/certs/r3vp-ca.crt"

    # Temporal
    temporal_address: str = "temporal.r3vp.io:7233"
    temporal_namespace: str = "r3vp-prod"
    temporal_task_queue: str = "recovery-validation"

    # Vault (SOPS-encrypted secrets file path)
    vault_secrets_path: str = "/vault/secrets.enc.yaml"
    vault_age_key_path: str = "/vault/age.key"

    # Veeam (populated from vault at runtime)
    veeam_base_url: str = ""
    veeam_username: str = ""
    veeam_password: SecretStr = SecretStr("")

    # vCenter (populated from vault at runtime)
    vcenter_host: str = ""
    vcenter_username: str = ""
    vcenter_password: SecretStr = SecretStr("")

    # Isolated test network
    isolated_vlan_id: int = 4090
    isolated_network_name: str = "r3vp-isolated"

    log_level: str = "INFO"

    # Threat intelligence settings
    threat_db_path: str = "/opt/r3vp/data/threat.db"
    threat_scan_paths: str = "/tmp,/var/tmp"       # comma-separated
    threat_scan_interval_secs: int = 3600
    threat_feed_url: str = "https://api.r3vp.io/v1/threat-feed"
    threat_feed_api_key: str = ""


settings = ApplianceSettings()
