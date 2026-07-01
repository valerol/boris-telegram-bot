from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from core_manager.core_loader import ACTIVE_LINK, CORE_ROOT, REGISTRY_PATH, load_registry
from core_manager.core_validator import ValidationResult, validate_core_package


VERSIONS_DIR = CORE_ROOT / "versions"
STAGING_DIR = CORE_ROOT / "staging"


def import_core(zip_path: Path) -> dict:
    source_zip = zip_path.resolve()
    if not source_zip.is_file():
        raise FileNotFoundError(f"ZIP file not found: {source_zip}")

    _ensure_core_dirs()
    incoming_dir = STAGING_DIR / f"_incoming_{_timestamp()}"
    incoming_dir.mkdir(parents=True, exist_ok=False)

    with zipfile.ZipFile(source_zip) as archive:
        _extract_zip_safely(archive, incoming_dir)

    package_root = detect_package_root(incoming_dir)
    version = detect_version(package_root)
    staging_version_dir = STAGING_DIR / version
    if staging_version_dir.exists():
        shutil.rmtree(staging_version_dir)
    incoming_dir.rename(staging_version_dir)

    package_root = detect_package_root(staging_version_dir)
    validation = validate_core_package(package_root)
    package_root_name = package_root.name

    if not validation.ok:
        current_registry = load_registry()
        registry = {
            **current_registry,
            **_registry_payload(
                version=None,
                active_path=None,
                previous_version=current_registry.get("previous_version"),
                source_zip=source_zip,
                validation=validation,
                package_root_name=package_root_name,
            ),
            "active_version": current_registry.get("active_version"),
            "active_path": current_registry.get("active_path"),
        }
        _write_registry(registry)
        return registry

    version_dir = VERSIONS_DIR / version
    if version_dir.exists():
        raise FileExistsError(f"Core version already exists: {version}")

    version_dir.mkdir(parents=True, exist_ok=False)
    shutil.copytree(package_root, version_dir / package_root_name)

    previous_version = load_registry().get("active_version")
    _activate_version(version)

    registry = _registry_payload(
        version=version,
        active_path=version_dir,
        previous_version=previous_version,
        source_zip=source_zip,
        validation=validation,
        package_root_name=package_root_name,
    )
    _write_registry(registry)
    return registry


def rollback_core() -> dict:
    registry = load_registry()
    previous_version = registry.get("previous_version")
    if not previous_version:
        raise RuntimeError("No previous core version available for rollback")
    previous_dir = VERSIONS_DIR / previous_version
    if not previous_dir.is_dir():
        raise RuntimeError(f"Previous core version is missing: {previous_version}")

    current_version = registry.get("active_version")
    _activate_version(previous_version)
    updated = {
        **registry,
        "active_version": previous_version,
        "active_path": str(previous_dir),
        "previous_version": current_version,
        "imported_at": _iso_now(),
        "validation_status": "rolled_back",
        "validation_errors": [],
    }
    _write_registry(updated)
    return updated


def detect_package_root(extracted_root: Path) -> Path:
    candidates = [
        path
        for path in extracted_root.rglob("integrity/manifest.json")
        if (path.parent.parent / "load_order.txt").is_file()
    ]
    if not candidates:
        candidates = list(extracted_root.rglob("integrity/manifest.json"))
    if not candidates:
        raise RuntimeError(f"Cannot detect BOIS Core package root under: {extracted_root}")
    roots = sorted({candidate.parent.parent for candidate in candidates}, key=lambda path: len(path.parts))
    return roots[0]


def detect_version(package_root: Path) -> str:
    manifest_path = package_root / "integrity" / "manifest.json"
    version = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        if isinstance(manifest, dict):
            version = (
                manifest.get("version")
                or manifest.get("manifest_version")
                or manifest.get("core_version")
                or manifest.get("package_version")
            )
    return _safe_version(str(version or package_root.name))


def _activate_version(version: str) -> None:
    target = Path("versions") / version
    tmp_link = CORE_ROOT / "active.tmp"
    if tmp_link.exists() or tmp_link.is_symlink():
        tmp_link.unlink()
    tmp_link.symlink_to(target)
    os.replace(tmp_link, ACTIVE_LINK)


def _registry_payload(
    version: str | None,
    active_path: Path | None,
    previous_version: str | None,
    source_zip: Path,
    validation: ValidationResult,
    package_root_name: str | None,
) -> dict:
    manifest = validation.manifest or {}
    manifest_version = (
        manifest.get("version")
        or manifest.get("manifest_version")
        or manifest.get("core_version")
        or manifest.get("package_version")
    )
    return {
        "active_version": version,
        "active_path": str(active_path) if active_path else None,
        "previous_version": previous_version,
        "imported_at": _iso_now(),
        "source_zip": str(source_zip),
        "validation_status": "passed" if validation.ok else "failed",
        "validation_errors": validation.errors,
        "manifest_version": manifest_version,
        "package_root_name": package_root_name,
        "file_count": validation.file_count,
    }


def _write_registry(registry: dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_core_dirs() -> None:
    for path in (CORE_ROOT, VERSIONS_DIR, STAGING_DIR, CORE_ROOT / "backups"):
        path.mkdir(parents=True, exist_ok=True)


def _extract_zip_safely(archive: zipfile.ZipFile, destination: Path) -> None:
    destination_root = destination.resolve()
    for member in archive.infolist():
        target = (destination_root / member.filename).resolve()
        if not _is_relative_to(target, destination_root):
            raise RuntimeError(f"Unsafe ZIP path: {member.filename}")
    archive.extractall(destination_root)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_version(version: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", version.strip()).strip("-._")
    return cleaned or _timestamp()
