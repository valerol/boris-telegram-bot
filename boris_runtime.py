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
from boris_execution.core_execution_filter import (
    apply_core_execution_filter,
    build_core_execution_filter,
    validate_against_execution_contract,
)
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

    def run(self, text: str, session_context: dict | None = None) -> dict:
        print("BOIS_RUNTIME_START")
        sima_analysis = parse(text)
        analysis = sima_analysis
        active_core = self._core_loader()
        analysis["active_core"] = build_core_context(active_core)
        extracted_contract = extract_contract_from_active_core(active_core)
        analysis["extracted_contract"] = extracted_contract.to_dict()

        domain = resolve_domain(text)
        analysis["domain"] = domain
        gate_decision = decide_capability(analysis, domain)
        analysis["gate"] = gate_decision.to_dict()
        core_execution_filter = build_core_execution_filter(
            active_core,
            sima_analysis,
            gate_decision,
        )
        print(
            "CORE_EXECUTION_FILTER_CREATED "
            f"mode={core_execution_filter.get('BORIS', {}).get('mode')} "
            f"response_boundary={core_execution_filter.get('EXECUTION_CONTROL', {}).get('response_boundary')}"
        )
        analysis["core_execution_filter"] = core_execution_filter
        enforced_execution_contract = apply_core_execution_filter(
            core_execution_filter,
            sima_analysis,
            gate_decision,
        )
        analysis["enforced_execution_contract"] = enforced_execution_contract
        analysis["session_core_context"] = _session_core_context(
            session_context or {},
            analysis["active_core"],
            analysis["extracted_contract"],
            core_execution_filter,
        )
        analysis["core_application_protocol"] = build_core_application_protocol(
            text,
            analysis,
            gate_decision.to_dict(),
        )

        if _requires_native_core(analysis) and not active_core.available:
            return _deterministic_output(analysis, CORE_UNAVAILABLE_RU)

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
            return _contract_output(analysis, contract, raw="", route="FALLBACK", llm_called=True)

        is_valid, execution_errors = validate_against_execution_contract(contract, enforced_execution_contract)
        if not is_valid:
            analysis["execution_contract_errors"] = execution_errors
            contract = fallback_contract(analysis, execution_errors)
            return _contract_output(analysis, contract, raw="", route="FALLBACK", llm_called=True)

        return _contract_output(analysis, contract, raw=raw_llm_output, route="CONSTRAINED_LLM", llm_called=True)

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
                "route": "FALLBACK",
            },
            "reasoning": {
                "raw": "",
            },
            "trace": _trace(analysis, "FALLBACK", llm_called=True),
            "metadata": _metadata(analysis),
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


def _contract_output(analysis: dict, contract: dict, raw: str, route: str = "LLM", llm_called: bool = False) -> dict:
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
        "trace": _trace(analysis, route, llm_called),
        "metadata": _metadata(analysis),
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


def _session_core_context(
    session_context: dict,
    active_core_summary: dict,
    extracted_contract: dict,
    execution_filter: dict,
) -> dict:
    return {
        "core_brief": session_context.get("core_brief", ""),
        "active_core_summary": active_core_summary,
        "extracted_contract": extracted_contract,
        "execution_filter_snapshot": execution_filter,
    }


def _trace(analysis: dict, route: str, llm_called: bool) -> dict:
    return {
        "route": route,
        "llm_called": llm_called,
        "core_used": bool((analysis.get("active_core") or {}).get("available")),
        "filter_applied": bool(analysis.get("core_execution_filter")),
    }


def _metadata(analysis: dict) -> dict:
    return {
        "core_execution_filter": analysis.get("core_execution_filter", {}),
        "enforced_execution_contract": analysis.get("enforced_execution_contract", {}),
        "execution_contract_errors": analysis.get("execution_contract_errors", []),
        "session_core_context": analysis.get("session_core_context", {}),
    }


def _display_core_path(path) -> str:
    if path is None:
        return "not available"
    parts = path.parts
    if "core" in parts:
        core_index = parts.index("core")
        return "/".join(parts[core_index:])
    return path.name
