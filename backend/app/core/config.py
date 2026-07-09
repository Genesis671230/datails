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

    @model_validator(mode="after")
    def _forbid_dev_mode_outside_local(self) -> "Settings":
        if self.auth_dev_mode and self.environment != ENVIRONMENT_LOCAL:
            raise ValueError(
                "AUTH_DEV_MODE=true is only permitted when ENVIRONMENT=local "
                "(LD-1). Refusing to start."
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
