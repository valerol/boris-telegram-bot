from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import core_manager.core_importer as core_importer
import core_manager.core_loader as core_loader


class CoreManagerTest(unittest.TestCase):
    def test_valid_import_updates_active_and_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = _make_core_zip(root, "1.0.0")

            with _patched_core(root):
                registry = core_importer.import_core(zip_path)
                active_core = core_loader.get_active_core()

            self.assertEqual(registry["validation_status"], "passed")
            self.assertEqual(registry["active_version"], "1.0.0")
            self.assertTrue((root / "core" / "active").is_symlink())
            self.assertTrue(active_core.available)
            self.assertEqual(active_core.core_version, "1.0.0")
            self.assertEqual(active_core.manifest["version"], "1.0.0")
            self.assertEqual(len(active_core.machine_json), 1)
            self.assertEqual(len(active_core.active_rules), 1)

    def test_invalid_core_does_not_activate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = _make_invalid_core_zip(root)

            with _patched_core(root):
                registry = core_importer.import_core(zip_path)
                active_core = core_loader.get_active_core()

            self.assertEqual(registry["validation_status"], "failed")
            self.assertFalse((root / "core" / "active").exists())
            self.assertFalse(active_core.available)
            self.assertTrue(registry["validation_errors"])

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = _make_core_zip(root, "2.0.0", bad_hash=True)

            with _patched_core(root):
                registry = core_importer.import_core(zip_path)

            self.assertEqual(registry["validation_status"], "failed")
            self.assertFalse((root / "core" / "active").exists())
            self.assertTrue(any("Hash mismatch" in error for error in registry["validation_errors"]))

    def test_unsafe_zip_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = root / "Unsafe_Core.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("../escape.txt", "escape")

            with _patched_core(root):
                with self.assertRaises(RuntimeError):
                    core_importer.import_core(zip_path)

            self.assertFalse((root / "escape.txt").exists())
            self.assertFalse((root / "core" / "active").exists())

    def test_rollback_restores_previous_active_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_zip = _make_core_zip(root, "1.0.0")
            second_zip = _make_core_zip(root, "1.1.0")

            with _patched_core(root):
                core_importer.import_core(first_zip)
                core_importer.import_core(second_zip)
                registry = core_importer.rollback_core()
                active_core = core_loader.get_active_core()

            self.assertEqual(registry["active_version"], "1.0.0")
            self.assertEqual(registry["previous_version"], "1.1.0")
            self.assertEqual(active_core.core_version, "1.0.0")


def _patched_core(root: Path):
    core_root = root / "core"
    registry_path = core_root / "registry.json"
    active_link = core_root / "active"
    patches = [
        patch.object(core_loader, "CORE_ROOT", core_root),
        patch.object(core_loader, "REGISTRY_PATH", registry_path),
        patch.object(core_loader, "ACTIVE_LINK", active_link),
        patch.object(core_importer, "CORE_ROOT", core_root),
        patch.object(core_importer, "VERSIONS_DIR", core_root / "versions"),
        patch.object(core_importer, "STAGING_DIR", core_root / "staging"),
        patch.object(core_importer, "REGISTRY_PATH", registry_path),
        patch.object(core_importer, "ACTIVE_LINK", active_link),
    ]
    return _PatchStack(patches)


class _PatchStack:
    def __init__(self, patches):
        self._patches = patches

    def __enter__(self):
        for item in self._patches:
            item.__enter__()

    def __exit__(self, exc_type, exc, tb):
        for item in reversed(self._patches):
            item.__exit__(exc_type, exc, tb)


def _make_core_zip(root: Path, version: str, bad_hash: bool = False) -> Path:
    package = root / f"BOIS_Core_{version}"
    _write_core_package(package, version)
    digest = hashlib.sha256((package / "load_order.txt").read_bytes()).hexdigest()
    if bad_hash:
        digest = "0" * 64
    (package / "integrity" / "hashes.sha256").write_text(f"{digest}  load_order.txt\n", encoding="utf-8")
    zip_path = root / f"BOIS_Core_{version}.zip"
    _zip_directory(package, zip_path)
    return zip_path


def _make_invalid_core_zip(root: Path) -> Path:
    package = root / "Invalid_Core"
    (package / "integrity").mkdir(parents=True)
    (package / "integrity" / "manifest.json").write_text("{}", encoding="utf-8")
    zip_path = root / "Invalid_Core.zip"
    _zip_directory(package, zip_path)
    return zip_path


def _write_core_package(package: Path, version: str) -> None:
    for relative in ("integrity", "runtime", "core", "tables"):
        (package / relative).mkdir(parents=True, exist_ok=True)
    (package / "integrity" / "manifest.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    (package / "integrity" / "validation_report.json").write_text("{}", encoding="utf-8")
    (package / "load_order.txt").write_text("core/main.machine.json\n", encoding="utf-8")
    (package / "language_policy.json").write_text("{}", encoding="utf-8")
    (package / "runtime" / "surface_contract.json").write_text("{}", encoding="utf-8")
    (package / "core" / "conflict_policy.json").write_text("{}", encoding="utf-8")
    (package / "core" / "main.machine.json").write_text("{}", encoding="utf-8")
    for filename in ("active_rules.csv", "stop_signals.csv", "procedures.csv", "criteria.csv"):
        (package / "tables" / filename).write_text("id,name\n1,test\n", encoding="utf-8")


def _zip_directory(package: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in package.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package.parent))


if __name__ == "__main__":
    unittest.main()
