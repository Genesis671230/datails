"""Secret resolver interface.

Connectors store a `secret_ref` only — never a raw secret (01 §3). The
resolver turns a ref into the secret value at call time. Azure Key Vault
implements this at Slice 3; local development resolves refs from environment
variables.
"""

from abc import ABC, abstractmethod


class SecretResolutionError(Exception):
    """Raised when a secret_ref cannot be resolved. The message must never
    contain secret material."""


class SecretResolver(ABC):
    @abstractmethod
    async def get_secret(self, secret_ref: str) -> str:
        """Resolve secret_ref to its value; raise SecretResolutionError if absent."""
