from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_FILES = (
    "integrity/manifest.json",
    "integrity/hashes.sha256",
    "integrity/validation_report.json",
    "load_order.txt",
    "language_policy.json",
    "runtime/surface_contract.json",
    "core/conflict_policy.json",
    "tables/active_rules.csv",
    "tables/stop_signals.csv",
    "tables/procedures.csv",
    "tables/criteria.csv",
)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    manifest: dict | None = None
    file_count: int = 0


def validate_core_package(package_root: Path) -> ValidationResult:
    root = package_root.resolve()
    errors: list[str] = []

    if not root.exists() or not root.is_dir():
        return ValidationResult(False, [f"Package root does not exist: {root}"])

    for relative_path in REQUIRED_FILES:
        if not (root / relative_path).is_file():
            errors.append(f"Missing required file: {relative_path}")

    if not any((root / "core").glob("*.machine.json")):
        errors.append("Missing required machine JSON: core/*.machine.json")

    manifest = _load_manifest(root / "integrity" / "manifest.json", errors)

    hashes_file = root / "integrity" / "hashes.sha256"
    if hashes_file.is_file():
        errors.extend(_verify_hashes(root, hashes_file))

    file_count = sum(1 for path in root.rglob("*") if path.is_file())
    return ValidationResult(ok=not errors, errors=errors, manifest=manifest, file_count=file_count)


def _load_manifest(path: Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        errors.append(f"Invalid manifest.json: {error}")
        return None
    if not isinstance(loaded, dict):
        errors.append("manifest.json must contain a JSON object")
        return None
    return loaded


def _verify_hashes(root: Path, hashes_file: Path) -> list[str]:
    errors: list[str] = []
    try:
        lines = hashes_file.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return [f"Cannot read hashes.sha256: {error}"]

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = _parse_hash_line(stripped)
        if parsed is None:
            errors.append(f"Invalid hashes.sha256 line {line_number}: {line}")
            continue
        expected_hash, relative_path = parsed
        target = (root / relative_path).resolve()
        if not _is_relative_to(target, root):
            errors.append(f"Hash path escapes package root: {relative_path}")
            continue
        if not target.is_file():
            errors.append(f"Hash target missing: {relative_path}")
            continue
        actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual_hash.lower() != expected_hash.lower():
            errors.append(f"Hash mismatch: {relative_path}")
    return errors


def _parse_hash_line(line: str) -> tuple[str, str] | None:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return None
    expected_hash, path_part = parts
    if len(expected_hash) != 64 or any(char not in "0123456789abcdefABCDEF" for char in expected_hash):
        return None
    relative_path = path_part.strip()
    if relative_path.startswith("*"):
        relative_path = relative_path[1:]
    return expected_hash, relative_path.strip()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
