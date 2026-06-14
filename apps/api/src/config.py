from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="R3VP_API_", env_file=".env")

    database_url: str = "postgresql+asyncpg://r3vp:r3vp@localhost:5432/r3vp"
    redis_url: str = "redis://localhost:6379/0"

    # AWS
    aws_region: str = "us-east-1"
    s3_evidence_bucket: str = "r3vp-evidence"

    # Auth0
    auth0_domain: str = ""
    auth0_audience: str = ""

    # mTLS — for verifying appliance client certs
    mtls_ca_path: str = "/certs/r3vp-ca.crt"

    # Temporal Cloud
    temporal_address: str = "temporal.r3vp.io:7233"
    temporal_namespace: str = "r3vp-prod"
    temporal_task_queue: str = "recovery-validation"
    temporal_cert_path: str = "/certs/temporal.crt"
    temporal_key_path: str = "/certs/temporal.key"

    log_level: str = "INFO"


settings = APISettings()
