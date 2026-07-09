"""Blob storage interface (Layer 2).

Raw connector payloads are snapshotted into tenant-controlled storage before
they become operational state (LD-4). The interface is deliberately small:
put bytes, get bytes, opaque storage_ref strings. Azure Blob implements this
at Slice 3; local development and CI use the filesystem implementation.
"""

from abc import ABC, abstractmethod


class BlobStorage(ABC):
    @abstractmethod
    async def put(self, container: str, name: str, payload: bytes) -> str:
        """Store payload; return an opaque storage_ref."""

    @abstractmethod
    async def get(self, storage_ref: str) -> bytes:
        """Fetch a payload previously stored under storage_ref."""
