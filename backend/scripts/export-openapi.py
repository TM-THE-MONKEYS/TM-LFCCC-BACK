#!/usr/bin/env python3
"""Export OpenAPI JSON from the FastAPI app (no server required).

Usage (from backend/):
  python scripts/export-openapi.py
  python scripts/export-openapi.py --out openapi.json

Generate TypeScript types (requires Node + openapi-typescript):
  npx openapi-typescript openapi.json -o api-contract.d.ts

See docs/api-contract.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path when invoked as a script.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("ENVIRONMENT", "test")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Vitrine OpenAPI schema")
    parser.add_argument(
        "--out",
        type=Path,
        default=_BACKEND_ROOT / "openapi.json",
        help="Output path for openapi.json",
    )
    args = parser.parse_args()

    from app.main import create_app

    schema = create_app().openapi()
    args.out.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
