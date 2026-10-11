"""Write the API's OpenAPI schema to a file, for generating the frontend's TypeScript types.

Run from `backend/`:  uv run python -m scripts.export_openapi ../frontend/openapi.json
CI runs the same command and fails if the committed schema is out of date.
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    """Write the schema to the path given on the command line."""
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.export_openapi <output.json>")
    schema = json.dumps(app.openapi(), indent=2, ensure_ascii=False)
    # Always LF, so the file is identical on Windows and in CI.
    Path(sys.argv[1]).write_text(schema + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
