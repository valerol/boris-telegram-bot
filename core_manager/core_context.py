from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core_manager.core_loader import ActiveCore


MAX_MACHINE_JSON_ITEMS = 2
MAX_ACTIVE_RULES = 8
MAX_STOP_SIGNALS = 12
MAX_PROCEDURES = 8
MAX_CRITERIA = 8
MAX_STRING_CHARS = 220
MAX_DICT_ITEMS = 15
MAX_LIST_ITEMS = 15
MAX_MACHINE_SNIPPETS = 24


def build_core_context(active_core: ActiveCore) -> dict:
    package_sha256, file_count = hash_core_package(active_core.active_path)
    loaded_surface = loaded_core_surface(active_core)
    loaded_surface_sha256 = hash_json(loaded_surface) if active_core.available else None

    context = {
        "available": active_core.available,
        "version": active_core.detected_version,
        "path": str(active_core.active_path) if active_core.active_path else None,
        "validation_status": active_core.validation_status,
        "validation_errors": active_core.validation_errors,
        "identity": {
            "package_sha256": package_sha256,
            "loaded_surface_sha256": loaded_surface_sha256,
            "file_count": file_count,
        },
    }

    if not active_core.available:
        return context

    context.update(
        {
            "load_order": active_core.load_order,
            "surface_contract": _bounded_value(active_core.surface_contract),
            "conflict_policy": _bounded_value(active_core.conflict_policy),
            "language_policy": _bounded_value(active_core.language_policy),
            "active_rules": _bounded_records(active_core.active_rules, MAX_ACTIVE_RULES),
            "stop_signals": _bounded_records(active_core.stop_signals, MAX_STOP_SIGNALS),
            "procedures": _bounded_records(active_core.procedures, MAX_PROCEDURES),
            "criteria": _bounded_records(active_core.criteria, MAX_CRITERIA),
            "machine_json": _machine_json_context(active_core.machine_json),
            "content_limits": {
                "machine_json": _limit_info(active_core.machine_json, MAX_MACHINE_JSON_ITEMS),
                "active_rules": _limit_info(active_core.active_rules, MAX_ACTIVE_RULES),
                "stop_signals": _limit_info(active_core.stop_signals, MAX_STOP_SIGNALS),
                "procedures": _limit_info(active_core.procedures, MAX_PROCEDURES),
                "criteria": _limit_info(active_core.criteria, MAX_CRITERIA),
            },
        }
    )
    return context


def loaded_core_surface(active_core: ActiveCore) -> dict:
    return {
        "manifest": active_core.manifest,
        "validation_report": active_core.validation_report,
        "machine_json": active_core.machine_json,
        "active_rules": active_core.active_rules,
        "stop_signals": active_core.stop_signals,
        "procedures": active_core.procedures,
        "criteria": active_core.criteria,
        "surface_contract": active_core.surface_contract,
        "conflict_policy": active_core.conflict_policy,
        "language_policy": active_core.language_policy,
        "load_order": active_core.load_order,
    }


def hash_core_package(root: Path | None) -> tuple[str | None, int]:
    if root is None or not root.is_dir():
        return None, 0

    digest = hashlib.sha256()
    file_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        file_count += 1
    return digest.hexdigest(), file_count


def hash_json(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _limited(items: list, limit: int) -> list:
    return list(items[:limit])


def _bounded_records(items: list, limit: int) -> list:
    return [_bounded_value(item) for item in _limited(items, limit)]


def _machine_json_context(items: list) -> list:
    context = []
    for item in _limited(items, MAX_MACHINE_JSON_ITEMS):
        if isinstance(item, dict):
            context.append(
                {
                    "top_level_keys": list(item.keys())[:MAX_DICT_ITEMS],
                    "scalar_snippets": list(_scalar_snippets(item))[:MAX_MACHINE_SNIPPETS],
                }
            )
        else:
            context.append(_bounded_value(item))
    return context


def _scalar_snippets(value):
    if isinstance(value, dict):
        for key, item in value.items():
            for snippet in _scalar_snippets(item):
                yield {str(key): snippet}
    elif isinstance(value, list):
        for item in value[:MAX_LIST_ITEMS]:
            yield from _scalar_snippets(item)
    elif isinstance(value, (str, int, float, bool)):
        yield _bounded_value(str(value))


def _bounded_value(value):
    if isinstance(value, dict):
        bounded = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_DICT_ITEMS:
                bounded["_truncated_keys"] = len(value) - MAX_DICT_ITEMS
                break
            bounded[key] = _bounded_value(item)
        return bounded
    if isinstance(value, list):
        bounded = [_bounded_value(item) for item in value[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            bounded.append({"_truncated_items": len(value) - MAX_LIST_ITEMS})
        return bounded
    if isinstance(value, str):
        if len(value) <= MAX_STRING_CHARS:
            return value
        return value[:MAX_STRING_CHARS] + f"... [truncated {len(value) - MAX_STRING_CHARS} chars]"
    return value


def _limit_info(items: list, limit: int) -> dict:
    return {
        "included": min(len(items), limit),
        "total": len(items),
        "truncated": len(items) > limit,
    }
