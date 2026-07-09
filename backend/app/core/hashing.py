"""Payload serialization and hashing (LD-3/LD-4).

Every snapshot and ledger entry carries a SHA-256 of the exact bytes written
to storage. Canonical JSON (sorted keys, no whitespace variance) keeps hashes
stable for logically-equal payloads.
"""

import hashlib
import json


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
