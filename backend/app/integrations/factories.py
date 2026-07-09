"""Backend selection for storage and secrets.

One place decides which implementation runs, driven by settings. Azure
implementations are added at Slice 3 behind the same interfaces.
"""

from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.integrations.blob_storage.base import BlobStorage
from app.integrations.blob_storage.local import LocalBlobStorage
from app.integrations.key_vault.base import SecretResolver
from app.integrations.key_vault.local import EnvSecretResolver


@lru_cache
def get_blob_storage() -> BlobStorage:
    settings = get_settings()
    if settings.blob_backend == "local":
        return LocalBlobStorage(Path(settings.blob_local_path))
    raise NotImplementedError(
        f"blob backend {settings.blob_backend!r} arrives with the Slice 3 deploy"
    )


@lru_cache
def get_secret_resolver() -> SecretResolver:
    settings = get_settings()
    if settings.secrets_backend == "local_env":
        return EnvSecretResolver()
    raise NotImplementedError(
        f"secrets backend {settings.secrets_backend!r} arrives with the Slice 3 deploy"
    )
