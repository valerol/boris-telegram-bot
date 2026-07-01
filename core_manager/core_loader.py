from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "core"
REGISTRY_PATH = CORE_ROOT / "registry.json"
ACTIVE_LINK = CORE_ROOT / "active"


@dataclass(frozen=True)
class ActiveCore:
    active_path: Path | None
    core_version: str | None
    manifest: dict | None = None
    validation_report: dict | None = None
    machine_json: list[dict] = field(default_factory=list)
    active_rules: list[dict] = field(default_factory=list)
    stop_signals: list[dict] = field(default_factory=list)
    procedures: list[dict] = field(default_factory=list)
    criteria: list[dict] = field(default_factory=list)
    surface_contract: dict | None = None
    conflict_policy: dict | None = None
    language_policy: dict | None = None
    load_order: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.active_path is not None


def get_active_core() -> ActiveCore:
    registry = load_registry()
    active_container = _active_path_from_registry(registry)
    if active_container is None or not active_container.is_dir():
        return ActiveCore(active_path=None, core_version=registry.get("active_version"))
    active_path = _detect_package_root(active_container)
    if active_path is None:
        return ActiveCore(active_path=None, core_version=registry.get("active_version"))

    return ActiveCore(
        active_path=active_path,
        core_version=registry.get("active_version"),
        manifest=_read_json(active_path / "integrity" / "manifest.json"),
        validation_report=_read_json(active_path / "integrity" / "validation_report.json"),
        machine_json=[_read_json(path) for path in sorted((active_path / "core").glob("*.machine.json"))],
        active_rules=_read_csv(active_path / "tables" / "active_rules.csv"),
        stop_signals=_read_csv(active_path / "tables" / "stop_signals.csv"),
        procedures=_read_csv(active_path / "tables" / "procedures.csv"),
        criteria=_read_csv(active_path / "tables" / "criteria.csv"),
        surface_contract=_read_json(active_path / "runtime" / "surface_contract.json"),
        conflict_policy=_read_json(active_path / "core" / "conflict_policy.json"),
        language_policy=_read_json(active_path / "language_policy.json"),
        load_order=_read_lines(active_path / "load_order.txt"),
    )


def load_registry() -> dict:
    if not REGISTRY_PATH.is_file():
        return {}
    try:
        loaded = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _active_path_from_registry(registry: dict) -> Path | None:
    if ACTIVE_LINK.exists() or ACTIVE_LINK.is_symlink():
        return ACTIVE_LINK.resolve()
    active_path = registry.get("active_path")
    if active_path:
        return Path(active_path)
    return None


def _detect_package_root(active_container: Path) -> Path | None:
    direct_manifest = active_container / "integrity" / "manifest.json"
    if direct_manifest.is_file() and (active_container / "load_order.txt").is_file():
        return active_container
    candidates = [
        path
        for path in active_container.rglob("integrity/manifest.json")
        if (path.parent.parent / "load_order.txt").is_file()
    ]
    if not candidates:
        return None
    roots = sorted({candidate.parent.parent for candidate in candidates}, key=lambda path: len(path.parts))
    return roots[0]


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def _read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
