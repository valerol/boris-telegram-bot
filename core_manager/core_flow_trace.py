from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from boris_domain import resolve_domain
from boris_formatter import present_answer
from boris_gate import decide_capability
from boris_llm import build_llm_prompt
from boris_protocol import scaffold_llm_output
from core_manager.core_loader import ActiveCore, get_active_core
from sima_analyzer import parse


TRACE_PLACEHOLDER_LLM_OUTPUT = "[diagnostic placeholder: LLM call not executed]"


@dataclass(frozen=True)
class CoreIdentity:
    available: bool
    root_path: str | None
    detected_version: str | None
    validation_status: str
    file_count: int
    package_sha256: str | None
    loaded_surface_sha256: str | None


def trace_core_information_flow(user_text: str, llm_output: str = TRACE_PLACEHOLDER_LLM_OUTPUT) -> dict:
    active_core = get_active_core()
    identity = _core_identity(active_core)
    analysis = parse(user_text)
    active_core_summary = _runtime_core_summary(active_core)
    analysis["active_core"] = active_core_summary

    stages = [
        _stage(
            name="core_loader.get_active_core",
            carrier="ActiveCore object",
            state="present" if active_core.available else "lost",
            identity=identity,
            evidence={
                "active_path": identity.root_path,
                "detected_version": identity.detected_version,
                "validation_status": identity.validation_status,
                "file_count": identity.file_count,
                "package_sha256": identity.package_sha256,
                "loaded_surface_sha256": identity.loaded_surface_sha256,
            },
            identity_assertable=active_core.available,
            notes="Native package files are still addressable through active_path when available.",
        ),
        _stage(
            name='boris_runtime.analysis["active_core"]',
            carrier="runtime analysis dict",
            state="reduced" if active_core.available else "lost",
            identity=identity,
            evidence=active_core_summary,
            identity_assertable=_contains_identity(active_core_summary, identity),
            notes="Runtime keeps availability/version/path/status/errors, not manifest, machine JSON, tables, policies, or package digest.",
        ),
    ]

    if _requires_native_core(analysis) and not active_core.available:
        stages.extend(
            [
                _stage(
                    name="boris_runtime.native_core_guard",
                    carrier="deterministic runtime branch",
                    state="lost",
                    identity=identity,
                    evidence={
                        "requires_native_core": True,
                        "core_available": False,
                        "llm_call_skipped": True,
                        "fallback_triggered": True,
                    },
                    identity_assertable=False,
                    notes="Runtime stops before gate, prompt construction, and LLM for BOIS/SIMA/BORIS requests without an available core.",
                ),
                _stage(
                    name="bot.py Telegram reply_text",
                    carrier='result["output"]["answer"]',
                    state="lost",
                    identity=identity,
                    evidence={
                        "telegram_answer_source": "deterministic core unavailable fallback",
                        "telegram_answer_contains_package_sha256": False,
                    },
                    identity_assertable=False,
                    notes="Telegram sends the deterministic fallback text.",
                ),
            ]
        )
        return {
            "user_text": user_text,
            "core_identity": identity.__dict__,
            "first_identity_loss_stage": _first_identity_loss(stages),
            "first_reduction_stage": _first_state(stages, "reduced"),
            "stages": stages,
        }

    domain = resolve_domain(user_text)
    analysis["domain"] = domain
    gate_decision = decide_capability(analysis, domain)
    analysis["gate"] = gate_decision.to_dict()
    prompt = build_llm_prompt(user_text, analysis, gate_decision.to_dict())
    scaffold = scaffold_llm_output(user_text, llm_output, analysis)
    telegram_answer = scaffold["output"]["answer"]
    presented_answer = present_answer(llm_output)

    stages.extend(
        [
        _stage(
            name="boris_gate.decide_capability",
            carrier="gate decision + analysis dict",
            state="reduced" if active_core.available else "lost",
            identity=identity,
            evidence={
                "decision": gate_decision.decision,
                "reason": gate_decision.reason,
                "analysis_active_core": active_core_summary,
            },
            identity_assertable=_contains_identity(active_core_summary, identity),
            notes="Gate receives the reduced active_core summary indirectly through analysis.",
        ),
        _stage(
            name="boris_llm.build_llm_prompt",
            carrier="LLM prompt string",
            state=_prompt_core_state(prompt, identity),
            identity=identity,
            evidence={
                "contains_version": _contains_text(prompt, identity.detected_version),
                "contains_active_path": _contains_text(prompt, identity.root_path),
                "contains_package_sha256": _contains_text(prompt, identity.package_sha256),
                "contains_loaded_surface_sha256": _contains_text(prompt, identity.loaded_surface_sha256),
                "contains_manifest": _contains_json_fragment(prompt, active_core.manifest),
                "contains_machine_json": _contains_json_fragment(prompt, active_core.machine_json),
                "prompt_length": len(prompt),
            },
            identity_assertable=_contains_text(prompt, identity.package_sha256)
            or _contains_text(prompt, identity.loaded_surface_sha256),
            notes="Prompt receives runtime metadata but not a verifiable native core identity digest.",
        ),
        _stage(
            name="runtime LLM boundary",
            carrier="raw LLM output",
            state="lost",
            identity=identity,
            evidence={
                "llm_call_executed": llm_output != TRACE_PLACEHOLDER_LLM_OUTPUT,
                "raw_output_length": len(llm_output),
                "raw_output_contains_package_sha256": _contains_text(llm_output, identity.package_sha256),
                "raw_output_contains_loaded_surface_sha256": _contains_text(llm_output, identity.loaded_surface_sha256),
            },
            identity_assertable=False,
            notes="The diagnostic cannot prove the model used native core content unless that identity was present in the prompt or output.",
        ),
        _stage(
            name="boris_protocol.scaffold_llm_output",
            carrier="runtime response dict",
            state="lost",
            identity=identity,
            evidence={
                "input_has_active_core": "active_core" in scaffold.get("input", {}),
                "reasoning_raw_length": len(scaffold.get("reasoning", {}).get("raw", "")),
                "output_answer_length": len(scaffold.get("output", {}).get("answer", "")),
                "output_contains_package_sha256": _contains_text(json.dumps(scaffold, ensure_ascii=False), identity.package_sha256),
            },
            identity_assertable=False,
            notes="Scaffold preserves raw LLM text and reduced parser input, not native core content identity.",
        ),
        _stage(
            name="boris_formatter.present_answer",
            carrier="clean answer text",
            state="lost",
            identity=identity,
            evidence={
                "answer_length": len(presented_answer),
                "answer_contains_package_sha256": _contains_text(presented_answer, identity.package_sha256),
            },
            identity_assertable=False,
            notes="Formatter works on LLM output only.",
        ),
        _stage(
            name="bot.py Telegram reply_text",
            carrier='result["output"]["answer"]',
            state="lost",
            identity=identity,
            evidence={
                "telegram_answer_length": len(telegram_answer),
                "telegram_answer_contains_package_sha256": _contains_text(telegram_answer, identity.package_sha256),
            },
            identity_assertable=False,
            notes="Telegram sends only the final answer string.",
        ),
        ]
    )

    return {
        "user_text": user_text,
        "core_identity": identity.__dict__,
        "first_identity_loss_stage": _first_identity_loss(stages),
        "first_reduction_stage": _first_state(stages, "reduced"),
        "stages": stages,
    }


def _requires_native_core(analysis: dict) -> bool:
    return bool(
        analysis.get("is_bois_related")
        or analysis.get("is_sima_related")
        or analysis.get("is_boris_related")
        or analysis.get("domain") in {
            "bois_core",
            "sima_analysis",
            "boris_runtime",
            "boris_protocol",
            "bois_boris_methodology",
            "bois_boris_implementation",
        }
    )


def _runtime_core_summary(active_core: ActiveCore) -> dict:
    return {
        "available": active_core.available,
        "version": active_core.detected_version,
        "path": str(active_core.active_path) if active_core.active_path else None,
        "validation_status": active_core.validation_status,
        "validation_errors": active_core.validation_errors,
    }


def _core_identity(active_core: ActiveCore) -> CoreIdentity:
    package_digest, file_count = _hash_directory(active_core.active_path)
    loaded_surface = {
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
    return CoreIdentity(
        available=active_core.available,
        root_path=str(active_core.active_path) if active_core.active_path else None,
        detected_version=active_core.detected_version,
        validation_status=active_core.validation_status,
        file_count=file_count,
        package_sha256=package_digest,
        loaded_surface_sha256=_hash_json(loaded_surface) if active_core.available else None,
    )


def _hash_directory(root: Path | None) -> tuple[str | None, int]:
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


def _hash_json(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stage(
    name: str,
    carrier: str,
    state: str,
    identity: CoreIdentity,
    evidence: dict,
    identity_assertable: bool,
    notes: str,
) -> dict:
    return {
        "stage": name,
        "carrier": carrier,
        "information_state": state,
        "core_present": state in {"present", "transformed", "reduced"},
        "same_information_identity_assertable": identity_assertable,
        "identity_basis": {
            "package_sha256": identity.package_sha256,
            "loaded_surface_sha256": identity.loaded_surface_sha256,
        },
        "evidence": evidence,
        "notes": notes,
    }


def _contains_identity(value, identity: CoreIdentity) -> bool:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return _contains_text(serialized, identity.package_sha256) or _contains_text(
        serialized,
        identity.loaded_surface_sha256,
    )


def _prompt_core_state(prompt: str, identity: CoreIdentity) -> str:
    if not identity.available:
        return "lost"
    if _contains_text(prompt, identity.package_sha256) or _contains_text(prompt, identity.loaded_surface_sha256):
        return "transformed"
    if _contains_text(prompt, identity.detected_version) or _contains_text(prompt, identity.root_path):
        return "reduced"
    return "lost"


def _contains_json_fragment(text: str, value) -> bool:
    if not value:
        return False
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) in text


def _contains_text(container: str, needle: str | None) -> bool:
    return bool(needle and needle in container)


def _first_identity_loss(stages: list[dict]) -> str | None:
    for stage in stages:
        if not stage["same_information_identity_assertable"]:
            return stage["stage"]
    return None


def _first_state(stages: list[dict], state: str) -> str | None:
    for stage in stages:
        if stage["information_state"] == state:
            return stage["stage"]
    return None
