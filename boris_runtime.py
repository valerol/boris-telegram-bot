from boris_domain import resolve_domain
from boris_formatter import render_boris_response
from boris_gate import ALLOW_WITH_SCOPE_LIMIT, CLARIFY, DENY_OUT_OF_SCOPE, decide_capability
from boris_llm import build_llm_prompt, build_response_format, call_llm
from boris_response_contract import (
    deterministic_contract,
    fallback_contract,
    parse_response_contract,
)
from boris_templates import CLARIFY_RU, CORE_UNAVAILABLE_RU, OUT_OF_SCOPE_RU
from core_manager.core_application import build_core_application_protocol
from core_manager.contract_extractor import extract_contract_from_active_core
from core_manager.core_context import build_core_context
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
        analysis["active_core"] = build_core_context(active_core)
        extracted_contract = extract_contract_from_active_core(active_core)
        analysis["extracted_contract"] = extracted_contract.to_dict()

        if _requires_native_core(analysis) and not active_core.available:
            return _deterministic_output(analysis, CORE_UNAVAILABLE_RU)

        domain = resolve_domain(text)
        analysis["domain"] = domain
        gate_decision = decide_capability(analysis, domain)
        analysis["gate"] = gate_decision.to_dict()
        analysis["core_application_protocol"] = build_core_application_protocol(
            text,
            analysis,
            gate_decision.to_dict(),
        )

        if gate_decision.decision == DENY_OUT_OF_SCOPE:
            contract = deterministic_contract(analysis, "out_of_scope", OUT_OF_SCOPE_RU)
            return _contract_output(analysis, contract, raw="", route="RULE")

        if gate_decision.decision == CLARIFY:
            contract = deterministic_contract(analysis, "unclear", CLARIFY_RU)
            return _contract_output(analysis, contract, raw="", route="RULE")

        prompt = build_llm_prompt(text, analysis, gate_decision.to_dict())
        response_format = build_response_format(extracted_contract)

        try:
            raw_llm_output = _call_llm(self._llm_call, prompt, response_format)
        except Exception:
            return self._llm_error_output(analysis)

        contract, errors = parse_response_contract(raw_llm_output, extracted_contract, analysis)
        if contract is None:
            contract = fallback_contract(analysis, errors)

        return _contract_output(analysis, contract, raw=raw_llm_output)

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
    contract = deterministic_contract(analysis, "unclear", answer)
    contract["next_step"] = ""
    contract["missing_info"] = []
    return _contract_output(analysis, contract, raw=answer, route="RULE")


def _contract_output(analysis: dict, contract: dict, raw: str, route: str = "LLM") -> dict:
    answer = render_boris_response(contract, analysis.get("extracted_contract"))
    return {
        "input": analysis,
        "bois": {
            "intent": analysis.get("intent", "general"),
            "risk": analysis.get("risk", 0.0),
            "uncertainty": analysis.get("uncertainty", 0.0),
            "route": route,
        },
        "reasoning": {
            "raw": raw,
        },
        "contract": contract,
        "output": {
            "answer": answer,
            "key_points": [],
        },
    }


def _call_llm(llm_call, prompt: str, response_format: dict) -> str:
    try:
        return llm_call(prompt, response_format=response_format)
    except TypeError:
        return llm_call(prompt)


def _display_core_path(path) -> str:
    if path is None:
        return "not available"
    parts = path.parts
    if "core" in parts:
        core_index = parts.index("core")
        return "/".join(parts[core_index:])
    return path.name
