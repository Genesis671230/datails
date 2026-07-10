"""Recorded Crystal response fixtures (mock/replay mode, 07 Slice 0).

Current fixtures are SYNTHETIC and provisional: Crystal payload shapes are
unknown until the LD-6 API spike (auth, endpoints, shapes, rate limits,
licensing). The spike replaces these files with real recorded responses and
documents findings in integrations/crystal/CRYSTAL_NOTES.md. The Slice 1
connector consumes fixtures through this module so the swap is file-only.

Address-keyed fixtures (fixtures/addresses/<address>.<mode>.json) serve the
placeholder AQ case so the Slice 3 trace loop replays deterministically;
lookup falls back to the generic per-mode fixture when no address file
exists.
"""

import json
import re
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ADDRESS_FIXTURES_DIR = FIXTURES_DIR / "addresses"

FIXTURE_NAMES = ("risk_check", "full_investigation")

_SAFE_ADDRESS = re.compile(r"^[A-Za-z0-9]+$")


def load_crystal_fixture(name: str, address: str | None = None) -> dict:
    """Load a recorded (currently synthetic) Crystal response.

    Prefers an address-keyed fixture when one exists for (address, mode).
    """
    if name not in FIXTURE_NAMES:
        raise ValueError(f"unknown Crystal fixture {name!r}; known: {FIXTURE_NAMES}")
    if address and _SAFE_ADDRESS.match(address):
        address_path = ADDRESS_FIXTURES_DIR / f"{address}.{name}.json"
        if address_path.exists():
            return json.loads(address_path.read_text())
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())
