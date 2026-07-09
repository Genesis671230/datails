"""Export the OpenAPI spec to docs/openapi.json (LD-26).

The spec is the frontend contract from Slice 0 onward. CI regenerates and
publishes it as an artifact; run manually after route changes:

    cd backend && .venv/bin/python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app  # noqa: E402

OUTPUT_PATH = Path(__file__).parent.parent.parent / "docs" / "openapi.json"


def main() -> None:
    app = create_app()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
