"""Unit tests: local blob storage, env secret resolver, hashing utility."""

from pathlib import Path

import pytest

from app.core.hashing import canonical_json_bytes, sha256_hex
from app.integrations.blob_storage.local import LocalBlobStorage
from app.integrations.key_vault.base import SecretResolutionError
from app.integrations.key_vault.local import EnvSecretResolver


async def test_local_blob_put_get_roundtrip(tmp_path: Path) -> None:
    storage = LocalBlobStorage(tmp_path)
    ref = await storage.put("snapshots", "tenant-x/payload.json", b'{"a": 1}')
    assert ref == "local://snapshots/tenant-x/payload.json"
    assert await storage.get(ref) == b'{"a": 1}'


async def test_local_blob_rejects_foreign_ref(tmp_path: Path) -> None:
    storage = LocalBlobStorage(tmp_path)
    with pytest.raises(ValueError, match="not a local storage_ref"):
        await storage.get("azure://container/name")


async def test_local_blob_rejects_path_escape(tmp_path: Path) -> None:
    storage = LocalBlobStorage(tmp_path)
    with pytest.raises(ValueError, match="escapes the blob root"):
        await storage.put("snapshots", "../../outside.json", b"x")


async def test_env_secret_resolver(monkeypatch) -> None:
    monkeypatch.setenv("SOME_TEST_SECRET", "value-123")
    resolver = EnvSecretResolver()
    assert await resolver.get_secret("SOME_TEST_SECRET") == "value-123"


async def test_env_secret_resolver_missing(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    resolver = EnvSecretResolver()
    with pytest.raises(SecretResolutionError, match="MISSING_SECRET"):
        await resolver.get_secret("MISSING_SECRET")


def test_canonical_json_is_stable() -> None:
    a = canonical_json_bytes({"b": 1, "a": [1, 2]})
    b = canonical_json_bytes({"a": [1, 2], "b": 1})
    assert a == b
    assert sha256_hex(a) == sha256_hex(b)
    assert len(sha256_hex(a)) == 64
