from boris_gate import ALLOW_WITH_SCOPE_LIMIT, CLARIFY, DENY_OUT_OF_SCOPE


def build_core_execution_filter(active_core, sima_analysis, gate_decision) -> dict:
    intent_class = _intent_class(sima_analysis)
    mode = _mode(sima_analysis, gate_decision)
    complexity = _complexity(sima_analysis)

    return {
        # SIMA ORG: classification and uncertainty modeling
        "SIMA": {
            "intent_class": intent_class,
            "complexity": complexity,
            "certainty": _certainty(sima_analysis),
            "opers_detected": _opers_detected(sima_analysis),
        },
        # BOIS ORG: epistemic constraint system
        "BOIS": {
            "must_separate": ["fact", "inference", "hypothesis"],
            "stop_conditions": _stop_conditions(sima_analysis, gate_decision),
            "authority_required": True,
            "no_unverified_completion": True,
        },
        # BORIS ORG: execution behavior control
        "BORIS": {
            "mode": mode,
            "reasoning_depth": _reasoning_depth(mode, complexity),
        },
        # SOCRATES ORG: state transition system
        "SOCRATES": {
            "input_state": "S_in",
            "output_state": "S_out",
            "required_delta": True,
            "closure_required": True,
        },
        # EXECUTION CONTROL: runtime enforcement layer
        "EXECUTION_CONTROL": {
            "must_apply_to_prompt": True,
            "response_boundary": "no_generic_assistant_behavior",
            "affects": {
                "SIMA": ["intent_class", "uncertainty"],
                "BOIS": ["stop_conditions", "fact_inference_split"],
                "BORIS": ["mode", "reasoning_depth"],
                "SOCRATES": ["state_transition", "closure"],
            },
        },
    }


def apply_core_execution_filter(core_execution_filter: dict, sima_analysis: dict, gate_decision) -> dict:
    boris_org = core_execution_filter.get("BORIS", {})
    bois_org = core_execution_filter.get("BOIS", {})
    execution_control = core_execution_filter.get("EXECUTION_CONTROL", {})
    mode = boris_org.get("mode", "explain")
    reasoning_depth = boris_org.get("reasoning_depth", "surface")

    return {
        "enforcement": "hard",
        "route": "CONSTRAINED_LLM",
        "allowed_reasoning_modes": [mode],
        "selected_reasoning_mode": mode,
        "reasoning_depth": reasoning_depth,
        "forbidden_response_forms": [
            "generic_consulting",
            "unstructured_freeform_answer",
            "raw_llm_output",
            "unsupported_external_domain_completion",
        ],
        "required_decomposition_steps": _required_decomposition_steps(mode, reasoning_depth),
        "mandatory_structure_compliance": {
            "must_use_bois_sima_boris_sections": True,
            "must_separate": bois_org.get("must_separate", ["fact", "inference", "hypothesis"]),
            "response_boundary": execution_control.get("response_boundary", "no_generic_assistant_behavior"),
        },
        "output_shape_constraints": {
            "required_contract_fields": [
                "scope_status",
                "request_type",
                "primary_domain",
                "applied_domain",
                "bois_section",
                "sima_section",
                "boris_section",
                "direct_answer",
                "boundary_note",
                "next_step",
                "confidence",
                "missing_info",
            ],
            "required_non_empty_when_in_scope": [
                "bois_section",
                "sima_section",
                "boris_section",
                "direct_answer",
                "next_step",
            ],
        },
        "stop_conditions": bois_org.get("stop_conditions", []),
        "source_filter_snapshot": core_execution_filter,
    }


def validate_against_execution_contract(contract: dict, enforced_execution_contract: dict) -> tuple[bool, list[str]]:
    errors = []
    if enforced_execution_contract.get("enforcement") != "hard":
        errors.append("Execution contract is not hard-enforced")

    allowed_modes = enforced_execution_contract.get("allowed_reasoning_modes") or []
    if not allowed_modes:
        errors.append("Execution contract has no allowed reasoning mode")

    required_fields = enforced_execution_contract.get("output_shape_constraints", {}).get("required_contract_fields", [])
    for field in required_fields:
        if field not in contract:
            errors.append(f"Missing execution contract output field: {field}")

    if contract.get("scope_status") == "in_scope":
        required_non_empty = enforced_execution_contract.get("output_shape_constraints", {}).get(
            "required_non_empty_when_in_scope",
            [],
        )
        for field in required_non_empty:
            if not str(contract.get(field) or "").strip():
                errors.append(f"Empty constrained LLM field: {field}")

    text = " ".join(
        str(contract.get(field) or "")
        for field in ("bois_section", "sima_section", "boris_section", "direct_answer", "boundary_note", "next_step")
    ).lower()
    forbidden_markers = {
        "generic_consulting": ("as a consultant", "generic consultant", "бизнес-консультант"),
        "unstructured_freeform_answer": ("here is a freeform answer", "свободный ответ"),
        "raw_llm_output": ("raw llm", "сырой ответ модели"),
        "unsupported_external_domain_completion": ("revenue forecast", "market sizing", "прогноз выручки"),
    }
    for response_form in enforced_execution_contract.get("forbidden_response_forms", []):
        for marker in forbidden_markers.get(response_form, ()):
            if marker in text:
                errors.append(f"Forbidden response form detected: {response_form}")
                break

    return not errors, errors


def _required_decomposition_steps(mode: str, reasoning_depth: str) -> list[str]:
    steps = ["BOIS_boundary", "SIMA_uncertainty", "BORIS_execution"]
    if reasoning_depth in {"structural", "physiological"}:
        steps.append("SOCRATES_closure")
    if mode in {"implement", "repair"}:
        steps.append("runtime_next_step")
    return steps


def _intent_class(sima_analysis: dict) -> str:
    if sima_analysis.get("is_bois_related") and sima_analysis.get("is_sima_related"):
        return "mixed"
    if sima_analysis.get("is_bois_related"):
        return "BOIS_query"
    if sima_analysis.get("is_sima_related"):
        return "SIMA_query"
    if sima_analysis.get("is_boris_related") or sima_analysis.get("requested_operation") in {
        "design_boris_runtime",
        "integrate_with_application",
        "integrate_with_llm",
    }:
        return "BORIS_integration"
    return "unknown"


def _complexity(sima_analysis: dict) -> str:
    if sima_analysis.get("requires_domain_expertise"):
        return "high"
    if sima_analysis.get("requested_operation") in {
        "analyze_through_sima",
        "design_boris_runtime",
        "integrate_with_application",
        "integrate_with_llm",
    }:
        return "medium"
    return "low"


def _certainty(sima_analysis: dict) -> str:
    uncertainty = float(sima_analysis.get("uncertainty", 0.0) or 0.0)
    if uncertainty >= 0.8:
        return "S0"
    if uncertainty >= 0.6:
        return "S1"
    if uncertainty >= 0.4:
        return "S2"
    if uncertainty >= 0.2:
        return "S3"
    return "S4"


def _opers_detected(sima_analysis: dict) -> list[str]:
    opers = []
    operation = sima_analysis.get("requested_operation")
    target = sima_analysis.get("target_object")
    if operation:
        opers.append(str(operation))
    if target and target != "unspecified":
        opers.append(str(target))
    return opers


def _mode(sima_analysis: dict, gate_decision) -> str:
    decision = getattr(gate_decision, "decision", None)
    if isinstance(gate_decision, dict):
        decision = gate_decision.get("decision")
    operation = sima_analysis.get("requested_operation")

    if decision == DENY_OUT_OF_SCOPE:
        return "refuse"
    if decision == CLARIFY:
        return "decompose"
    if operation in {"design_boris_runtime", "integrate_with_application", "integrate_with_llm"}:
        return "implement"
    if operation in {"analyze_through_sima", "analyze_through_bois"}:
        return "decompose"
    if operation == "repair_response":
        return "repair"
    if decision == ALLOW_WITH_SCOPE_LIMIT:
        return "simulate"
    return "explain"


def _reasoning_depth(mode: str, complexity: str) -> str:
    if mode in {"implement", "repair"} or complexity == "high":
        return "physiological"
    if mode in {"decompose", "simulate"} or complexity == "medium":
        return "structural"
    return "surface"


def _stop_conditions(sima_analysis: dict, gate_decision) -> list[str]:
    conditions = []
    decision = getattr(gate_decision, "decision", None)
    if isinstance(gate_decision, dict):
        decision = gate_decision.get("decision")
    if decision == DENY_OUT_OF_SCOPE:
        conditions.append("outside_boris_support_scope")
    if sima_analysis.get("missing_info"):
        conditions.append("missing_required_scope")
    if sima_analysis.get("requires_domain_expertise"):
        conditions.append("external_domain_expertise_required")
    return conditions
