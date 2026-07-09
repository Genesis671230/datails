"""Recorded Crystal response fixtures (mock/replay mode, 07 Slice 0).

Current fixtures are SYNTHETIC and provisional: Crystal payload shapes are
unknown until the LD-6 API spike (auth, endpoints, shapes, rate limits,
licensing). The spike replaces these files with real recorded responses and
documents findings in integrations/crystal/CRYSTAL_NOTES.md. The Slice 1
connector consumes fixtures through this module so the swap is file-only.
"""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_NAMES = ("risk_check", "full_investigation")


def load_crystal_fixture(name: str) -> dict:
    """Load a recorded (currently synthetic) Crystal response by name."""
    if name not in FIXTURE_NAMES:
        raise ValueError(f"unknown Crystal fixture {name!r}; known: {FIXTURE_NAMES}")
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())
