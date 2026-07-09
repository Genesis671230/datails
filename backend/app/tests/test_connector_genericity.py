"""Slice 1 acceptance: CONNECTOR GENERICITY (founder criterion, 9 Jul 2026).

No module outside integrations/crystal/ may import anything Crystal-specific.
The single allowed touchpoint is the connector registry
(app/integrations/registry.py). Tests are excluded: they exercise fixtures
directly but are not runtime modules.

Adding a second connector must require only integrations/<name>/ plus a
registry entry — this test keeps that true.
"""

import re
from pathlib import Path

APP_ROOT = Path(__file__).parent.parent  # backend/app

ALLOWED = {
    APP_ROOT / "integrations" / "registry.py",
}
EXCLUDED_DIRS = {
    APP_ROOT / "integrations" / "crystal",
    APP_ROOT / "tests",
}

CRYSTAL_IMPORT = re.compile(
    r"^\s*(from|import)\s+app\.integrations\.crystal\b", re.MULTILINE
)


def test_no_crystal_imports_outside_integration_and_registry() -> None:
    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        if path in ALLOWED or any(path.is_relative_to(d) for d in EXCLUDED_DIRS):
            continue
        if CRYSTAL_IMPORT.search(path.read_text()):
            violations.append(str(path.relative_to(APP_ROOT)))
    assert violations == [], (
        "Crystal-specific imports leaked outside integrations/crystal/ "
        f"(allowed touchpoint: integrations/registry.py): {violations}"
    )


def test_no_literal_crystal_knowledge_in_services() -> None:
    """Services must reference connectors via ConnectorType and generic
    contracts only — no fixture names, endpoints, or payload keys."""
    services_root = APP_ROOT / "services"
    forbidden = re.compile(r"load_crystal_fixture|crystal_fixture|CrystalConnector")
    violations = [
        str(path.relative_to(APP_ROOT))
        for path in services_root.rglob("*.py")
        if forbidden.search(path.read_text())
    ]
    assert violations == []
