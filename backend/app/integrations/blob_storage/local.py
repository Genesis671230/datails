"""Filesystem blob storage for local development and CI.

storage_ref format: local://<container>/<name>. Paths are confined to the
configured root; refs are validated on read so a crafted ref cannot escape it.
"""

from pathlib import Path

from app.integrations.blob_storage.base import BlobStorage

LOCAL_REF_PREFIX = "local://"


class LocalBlobStorage(BlobStorage):
    def __init__(self, root: Path):
        self._root = root.resolve()

    async def put(self, container: str, name: str, payload: bytes) -> str:
        path = self._resolve(container, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return f"{LOCAL_REF_PREFIX}{container}/{name}"

    async def get(self, storage_ref: str) -> bytes:
        if not storage_ref.startswith(LOCAL_REF_PREFIX):
            raise ValueError(f"not a local storage_ref: {storage_ref!r}")
        container, _, name = storage_ref.removeprefix(LOCAL_REF_PREFIX).partition("/")
        return self._resolve(container, name).read_bytes()

    def _resolve(self, container: str, name: str) -> Path:
        path = (self._root / container / name).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("storage path escapes the blob root")
        return path
