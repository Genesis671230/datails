"""Application configuration.

Single source of runtime configuration, loaded from environment variables
(and a local .env file in development). No secrets are ever hard-coded here;
in Azure, secret values arrive via Key Vault references in the container
environment (LD-1, security spec).
"""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENVIRONMENT_LOCAL = "local"


class Settings(BaseSettings):
    """Runtime settings for the Datails backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "datails-backend"
    environment: Literal["local", "dev", "staging", "prod"] = ENVIRONMENT_LOCAL
    log_level: str = "INFO"

    # Database — the application role is distinct from the migration role so
    # that LD-3 insert-only grants on the ledger tables actually bind at runtime.
    database_url: str = (
        "postgresql+asyncpg://datails_app:datails_app_local@localhost:5432/datails"
    )
    database_migration_url: str = (
        "postgresql+asyncpg://datails_owner:datails_owner_local@localhost:5432/datails"
    )

    # Authentication (LD-1) — Microsoft Entra External ID JWT validation.
    entra_tenant_id: str = ""
    entra_audience: str = ""
    entra_authority: str = ""  # e.g. https://<name>.ciamlogin.com/<tenant-id>/v2.0
    entra_jwks_url: str = ""  # derived from authority when empty

    # Local-development auth bypass (LD-1): permitted ONLY when environment is
    # "local". Startup hard-fails otherwise — this flag must never reach Azure.
    auth_dev_mode: bool = False
    dev_user_oid: str = "00000000-0000-0000-0000-000000000001"
    dev_user_email: str = "dev@localhost"

    # Storage and secret backends. Local implementations for dev/CI; Azure
    # implementations behind the same interfaces at the Slice 3 deploy.
    blob_backend: Literal["local", "azure"] = "local"
    blob_local_path: str = "./var/blobs"
    secrets_backend: Literal["local_env", "azure_key_vault"] = "local_env"

    # AI model backend. "mock" is deterministic for dev/CI; "azure_foundry"
    # calls the Datails Foundry instance (LD-24: Azure-hosted models only).
    # The mock is refused outside local environments.
    ai_backend: Literal["mock", "azure_foundry"] = "mock"
    foundry_endpoint: str = ""  # e.g. https://datails-dev-foundry.cognitiveservices.azure.com
    foundry_api_version: str = "2024-10-21"
    # API key resolved through the secret resolver (env locally, Key Vault in
    # Azure). Managed identity replaces the key at the ACA deploy.
    foundry_secret_ref: str = "FOUNDRY_API_KEY"

    # Crystal connector (LD-22). Transport "replay" serves recorded fixtures
    # (dev/CI); "live" calls the real API using the shared temporary key
    # resolved via secret_ref. Base URL and endpoint shapes are confirmed in
    # the LD-6 spike.
    crystal_transport: Literal["replay", "live"] = "replay"
    crystal_base_url: str = ""
    crystal_shared_secret_ref: str = "CRYSTAL_API_KEY"
    # Global daily budget for a Datails-shared key, across all tenants
    # (LD-22 shared-key arbitration; pilot: the shared Crystal key).
    shared_key_daily_budget: int = 500

    @model_validator(mode="after")
    def _forbid_dev_mode_outside_local(self) -> "Settings":
        if self.auth_dev_mode and self.environment != ENVIRONMENT_LOCAL:
            raise ValueError(
                "AUTH_DEV_MODE=true is only permitted when ENVIRONMENT=local "
                "(LD-1). Refusing to start."
            )
        if self.ai_backend == "mock" and self.environment not in (ENVIRONMENT_LOCAL, "dev"):
            raise ValueError(
                "AI_BACKEND=mock is only permitted in local/dev environments; "
                "production uses Azure-hosted models only (LD-24)."
            )
        return self

    @property
    def jwks_url(self) -> str:
        if self.entra_jwks_url:
            return self.entra_jwks_url
        return f"{self.entra_authority.rstrip('/')}/discovery/v2.0/keys"

    @property
    def expected_issuer(self) -> str:
        # Entra v2.0 tokens carry the authority URL as `iss` (no trailing slash).
        return self.entra_authority.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
