from __future__ import annotations

import json
from dataclasses import dataclass

from boris_domain import resolve_domain
from boris_formatter import render_boris_response
from boris_gate import decide_capability
from boris_llm import build_llm_prompt
from boris_response_contract import fallback_contract, parse_response_contract
from core_manager.core_application import build_core_application_protocol
from core_manager.core_context import build_core_context, hash_core_package, hash_json, loaded_core_surface
from core_manager.core_loader import ActiveCore, get_active_core
from sima_analyzer import parse


TRACE_PLACEHOLDER_LLM_OUTPUT = json.dumps(
    {
        "scope_status": "in_scope",
        "request_type": "diagnostic_trace",
        "primary_domain": "boris_support",
        "applied_domain": "diagnostic",
        "bois_section": "diagnostic BOIS section",
        "sima_section": "diagnostic SIMA section",
        "boris_section": "diagnostic BORIS section",
        "direct_answer": "diagnostic response contract",
        "boundary_note": "diagnostic boundary",
        "next_step": "diagnostic next step",
        "confidence": 0.5,
        "missing_info": [],
    },
    ensure_ascii=False,
)


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
    active_core_context = build_core_context(active_core)
    analysis["active_core"] = active_core_context

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
            state="transformed" if active_core.available else "lost",
            identity=identity,
            evidence=_context_evidence(active_core_context, identity),
            identity_assertable=_contains_identity(active_core_context, identity),
            notes="Runtime carries structured native core context with policies, tables, load order, selected machine JSON, and identity digests.",
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
    analysis["core_application_protocol"] = build_core_application_protocol(
        user_text,
        analysis,
        gate_decision.to_dict(),
    )
    prompt = build_llm_prompt(user_text, analysis, gate_decision.to_dict())
    contract, contract_errors = parse_response_contract(llm_output)
    if contract is None:
        contract = fallback_contract(analysis, contract_errors)
    telegram_answer = render_boris_response(contract)

    stages.extend(
        [
        _stage(
            name="boris_gate.decide_capability",
            carrier="gate decision + analysis dict",
            state="transformed" if active_core.available else "lost",
            identity=identity,
            evidence={
                "decision": gate_decision.decision,
                "reason": gate_decision.reason,
                "analysis_active_core": _context_evidence(active_core_context, identity),
            },
            identity_assertable=_contains_identity(active_core_context, identity),
            notes="Gate receives the structured active_core context indirectly through analysis.",
        ),
        _stage(
            name="core_manager.core_application.build_core_application_protocol",
            carrier="Core Application Protocol dict",
            state="transformed" if active_core.available else "lost",
            identity=identity,
            evidence={
                "core_loaded": bool(analysis["core_application_protocol"].get("core_loaded")),
                "core_application_protocol_present": True,
                "applicable_rules_count": len(analysis["core_application_protocol"].get("applicable_rules") or []),
                "applicable_stop_signals_count": len(
                    analysis["core_application_protocol"].get("applicable_stop_signals") or []
                ),
                "forbidden_moves_count": len(
                    analysis["core_application_protocol"].get("forbidden_answer_moves") or []
                ),
                "request_kind": analysis["core_application_protocol"].get("request_kind"),
            },
            identity_assertable=_contains_identity(analysis["core_application_protocol"], identity),
            notes="Protocol derives task-specific answer moves from selected loaded core rules and stop signals.",
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
                "contains_surface_contract_value": _contains_any_value(prompt, active_core.surface_contract),
                "contains_active_rule_value": _contains_any_value(prompt, active_core.active_rules),
                "core_application_protocol_present": "Core Application Protocol:" in prompt,
                "applicable_rules_count": len(analysis["core_application_protocol"].get("applicable_rules") or []),
                "forbidden_moves_count": len(
                    analysis["core_application_protocol"].get("forbidden_answer_moves") or []
                ),
                "prompt_length": len(prompt),
            },
            identity_assertable=_contains_text(prompt, identity.package_sha256)
            or _contains_text(prompt, identity.loaded_surface_sha256),
            notes="Prompt receives structured active_core context plus verifiable native core identity digests.",
        ),
        _stage(
            name="runtime LLM boundary",
            carrier="raw LLM output",
            state="transformed",
            identity=identity,
            evidence={
                "llm_call_executed": llm_output != TRACE_PLACEHOLDER_LLM_OUTPUT,
                "raw_output_length": len(llm_output),
                "raw_output_contains_package_sha256": _contains_text(llm_output, identity.package_sha256),
                "raw_output_contains_loaded_surface_sha256": _contains_text(llm_output, identity.loaded_surface_sha256),
            },
            identity_assertable=False,
            notes="The model boundary returns structured response contract data, but native core identity is not provable from output alone.",
        ),
        _stage(
            name="boris_response_contract.validate_response_contract",
            carrier="validated response contract",
            state="lost",
            identity=identity,
            evidence={
                "contract_valid": not contract_errors,
                "contract_errors": contract_errors,
                "scope_status": contract.get("scope_status"),
                "contract_contains_package_sha256": _contains_text(
                    json.dumps(contract, ensure_ascii=False),
                    identity.package_sha256,
                ),
            },
            identity_assertable=False,
            notes="Validation checks structure, not final-answer keywords.",
        ),
        _stage(
            name="boris_formatter.render_boris_response",
            carrier="Telegram-visible answer text",
            state="lost",
            identity=identity,
            evidence={
                "answer_length": len(telegram_answer),
                "answer_contains_package_sha256": _contains_text(telegram_answer, identity.package_sha256),
            },
            identity_assertable=False,
            notes="Formatter creates the final visible text from the validated response contract.",
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


def _core_identity(active_core: ActiveCore) -> CoreIdentity:
    package_digest, file_count = hash_core_package(active_core.active_path)
    loaded_surface = loaded_core_surface(active_core)
    return CoreIdentity(
        available=active_core.available,
        root_path=str(active_core.active_path) if active_core.active_path else None,
        detected_version=active_core.detected_version,
        validation_status=active_core.validation_status,
        file_count=file_count,
        package_sha256=package_digest,
        loaded_surface_sha256=hash_json(loaded_surface) if active_core.available else None,
    )


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


def _context_evidence(context: dict, identity: CoreIdentity) -> dict:
    return {
        "available": context.get("available"),
        "version": context.get("version"),
        "path": context.get("path"),
        "validation_status": context.get("validation_status"),
        "has_load_order": bool(context.get("load_order")),
        "has_surface_contract": bool(context.get("surface_contract")),
        "has_conflict_policy": bool(context.get("conflict_policy")),
        "has_language_policy": bool(context.get("language_policy")),
        "active_rules_count": len(context.get("active_rules") or []),
        "stop_signals_count": len(context.get("stop_signals") or []),
        "procedures_count": len(context.get("procedures") or []),
        "criteria_count": len(context.get("criteria") or []),
        "machine_json_count": len(context.get("machine_json") or []),
        "contains_package_sha256": _contains_identity_value(context, identity.package_sha256),
        "contains_loaded_surface_sha256": _contains_identity_value(context, identity.loaded_surface_sha256),
    }


def _contains_json_fragment(text: str, value) -> bool:
    if not value:
        return False
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) in text


def _contains_text(container: str, needle: str | None) -> bool:
    return bool(needle and needle in container)


def _contains_identity_value(value, needle: str | None) -> bool:
    return _contains_text(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str), needle)


def _contains_any_value(container: str, value) -> bool:
    for item in _scalar_values(value):
        if item and item in container:
            return True
    return False


def _scalar_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _scalar_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _scalar_values(item)
    elif isinstance(value, (str, int, float, bool)):
        text = str(value)
        if len(text) >= 3:
            yield text


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
