from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_manager.core_loader import get_active_core, load_registry


def main() -> None:
    active_core = get_active_core()
    registry = load_registry()
    payload = {
        "registry": registry,
        "active_core": {
            "available": active_core.available,
            "active_path": str(active_core.active_path) if active_core.active_path else None,
            "core_version": active_core.core_version,
            "machine_json_count": len(active_core.machine_json),
            "active_rules_count": len(active_core.active_rules),
            "stop_signals_count": len(active_core.stop_signals),
            "procedures_count": len(active_core.procedures),
            "criteria_count": len(active_core.criteria),
            "load_order_count": len(active_core.load_order),
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
