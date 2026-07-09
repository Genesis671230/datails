"""Environment-variable secret resolver for local development and CI.

A secret_ref like "CRYSTAL_API_KEY" resolves to the environment variable of
the same name. Mirrors Key Vault semantics (ref in, value out) so connector
code is identical in both environments.
"""

import os

from app.integrations.key_vault.base import SecretResolutionError, SecretResolver


class EnvSecretResolver(SecretResolver):
    async def get_secret(self, secret_ref: str) -> str:
        value = os.environ.get(secret_ref)
        if not value:
            raise SecretResolutionError(
                f"secret_ref {secret_ref!r} is not set in the local environment"
            )
        return value
