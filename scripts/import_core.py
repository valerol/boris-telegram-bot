from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_manager.core_importer import import_core


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and activate a native BOIS Core ZIP package.")
    parser.add_argument("zip_path", help="Path to BOIS Core ZIP file")
    args = parser.parse_args()

    registry = import_core(Path(args.zip_path))
    print(json.dumps(registry, ensure_ascii=False, indent=2))
    if registry.get("validation_status") != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
