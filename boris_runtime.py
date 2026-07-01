from boris_domain import resolve_domain
from boris_gate import ALLOW_WITH_SCOPE_LIMIT, CLARIFY, DENY_OUT_OF_SCOPE, decide_capability
from boris_llm import build_llm_prompt, call_llm
from boris_protocol import scaffold_llm_output
from boris_templates import CLARIFY_RU, CORE_UNAVAILABLE_RU, OUT_OF_SCOPE_RU, SCOPE_LIMIT_PREFIX_RU
from core_manager.core_loader import get_active_core
from sima_analyzer import parse


LLM_ERROR_MESSAGE = "LLM call failed. Please check OPENAI_API_KEY and runtime logs."


class BOISRuntime:
    def __init__(self, llm_call=call_llm, core_loader=get_active_core) -> None:
        self._llm_call = llm_call
        self._core_loader = core_loader

    def run(self, text: str) -> dict:
        print("BOIS_RUNTIME_START")
        analysis = parse(text)
        active_core = self._core_loader()
        analysis["active_core"] = {
            "available": active_core.available,
            "version": active_core.detected_version,
            "path": str(active_core.active_path) if active_core.active_path else None,
            "validation_status": active_core.validation_status,
            "validation_errors": active_core.validation_errors,
        }

        if _requires_native_core(analysis) and not active_core.available:
            return _deterministic_output(analysis, CORE_UNAVAILABLE_RU)

        domain = resolve_domain(text)
        analysis["domain"] = domain
        gate_decision = decide_capability(analysis, domain)
        analysis["gate"] = gate_decision.to_dict()

        if gate_decision.decision == DENY_OUT_OF_SCOPE:
            return scaffold_llm_output(text, OUT_OF_SCOPE_RU, analysis)

        if gate_decision.decision == CLARIFY:
            return scaffold_llm_output(text, CLARIFY_RU, analysis)

        prompt = build_llm_prompt(text, analysis, gate_decision.to_dict())

        try:
            raw_llm_output = self._llm_call(prompt)
        except Exception:
            return self._llm_error_output(analysis)

        if gate_decision.decision == ALLOW_WITH_SCOPE_LIMIT:
            raw_llm_output = f"{SCOPE_LIMIT_PREFIX_RU}\n\n{raw_llm_output}"

        return scaffold_llm_output(text, raw_llm_output, analysis)

    def status_core(self) -> str:
        active_core = self._core_loader()
        found = "yes" if active_core.available else "no"
        version = active_core.detected_version or "not detected"
        path = _display_core_path(active_core.active_path)
        status = active_core.validation_status

        return (
            f"Active core found: {found}\n"
            f"Detected version: {version}\n"
            f"Active path: {path}\n"
            f"Validation status: {status}"
        )

    def _llm_error_output(self, analysis: dict) -> dict:
        return {
            "input": analysis,
            "bois": {
                "intent": analysis.get("intent", "general"),
                "risk": analysis.get("risk", 0.0),
                "uncertainty": analysis.get("uncertainty", 0.0),
                "route": "LLM",
            },
            "reasoning": {
                "raw": "",
            },
            "output": {
                "answer": LLM_ERROR_MESSAGE,
                "key_points": [],
            },
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


def _deterministic_output(analysis: dict, answer: str) -> dict:
    return {
        "input": analysis,
        "bois": {
            "intent": analysis.get("intent", "general"),
            "risk": analysis.get("risk", 0.0),
            "uncertainty": analysis.get("uncertainty", 0.0),
            "route": "RULE",
        },
        "reasoning": {
            "raw": answer,
        },
        "output": {
            "answer": answer,
            "key_points": [],
        },
    }


def _display_core_path(path) -> str:
    if path is None:
        return "not available"
    parts = path.parts
    if "core" in parts:
        core_index = parts.index("core")
        return "/".join(parts[core_index:])
    return path.name
