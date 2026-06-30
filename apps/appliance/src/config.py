from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Multi-cloud provider settings
    provider: str = "vmware"   # "vmware", "hyperv", "azure", "aws"

    # AWS Backup settings
    aws_region: str = "us-east-1"
    aws_backup_vault: str = ""
    aws_target_subnet_id: str = ""
    aws_target_security_group_id: str = ""
    aws_iam_role_arn: str = ""

    # Azure Backup settings
    azure_subscription_id: str = ""
    azure_tenant_id: str = ""
    azure_vault_name: str = ""
    azure_resource_group: str = ""
    azure_target_resource_group: str = ""
    azure_target_vnet_id: str = ""
    azure_target_subnet_name: str = "r3vp-isolated"

    # Hyper-V settings
    hyperv_host: str = "localhost"

    # Proxmox
    proxmox_host: str = ""
    proxmox_user: str = "root@pam"
    proxmox_password: SecretStr = SecretStr("")
    proxmox_verify_ssl: bool = True
    proxmox_node: str = "pve"

    # Nutanix Prism Central
    nutanix_prism_host: str = ""
    nutanix_username: str = "admin"
    nutanix_password: SecretStr = SecretStr("")
    nutanix_verify_ssl: bool = False

    # RHV / oVirt
    rhv_url: str = ""
    rhv_username: str = "admin@internal"
    rhv_password: SecretStr = SecretStr("")
    rhv_ca_file: str = ""

    # XenServer / Citrix Hypervisor
    xenserver_host: str = ""
    xenserver_username: str = "root"
    xenserver_password: SecretStr = SecretStr("")

    # Sangfor HCI
    sangfor_host: str = ""
    sangfor_username: str = "admin"
    sangfor_password: SecretStr = SecretStr("")
    sangfor_verify_ssl: bool = False

    # GCP
    gcp_project_id: str = ""
    gcp_zone: str = "us-central1-a"
    gcp_backup_vault: str = ""
    gcp_target_network: str = ""
    gcp_target_subnetwork: str = ""
    gcp_service_account_json: str = ""

    # Threat intelligence settings
    threat_db_path: str = "/opt/r3vp/data/threat.db"
    threat_scan_paths: str = "/tmp,/var/tmp"       # comma-separated
    threat_scan_interval_secs: int = 3600
    threat_feed_url: str = "https://api.r3vp.io/v1/threat-feed"
    threat_feed_api_key: str = ""


settings = ApplianceSettings()
