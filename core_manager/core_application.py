from __future__ import annotations


CORE_APPLICATION_RULE_IDS = ("CORE-01", "CORE-02", "CORE-04", "CORE-05", "CORE-08")


def build_core_application_protocol(user_text: str, analysis: dict, gate_decision: dict) -> dict:
    active_core = analysis.get("active_core") or {}
    applicable_rules = _select_applicable_rules(active_core)
    applicable_stop_signals = _select_applicable_stop_signals(active_core)
    external_boris_request = _is_external_domain_with_boris(analysis)

    return {
        "core_loaded": bool(active_core.get("available")),
        "core_version": active_core.get("version"),
        "gate_decision": gate_decision.get("decision"),
        "request_kind": _request_kind(analysis, external_boris_request),
        "applicable_rules": applicable_rules,
        "applicable_stop_signals": applicable_stop_signals,
        "required_answer_moves": _required_moves(external_boris_request),
        "forbidden_answer_moves": _forbidden_moves(external_boris_request),
        "scope_boundary": _scope_boundary(analysis, external_boris_request),
        "self_check": [
            "Did I answer as BORIS Support, or did I become a generic consultant?",
            "Did I apply the selected native BOIS Core rules before answering?",
            "Did I mark unknowns, scope limits, and hypotheses explicitly?",
        ],
        "source_identity": active_core.get("identity", {}),
        "user_text_observed": user_text,
    }


def _select_applicable_rules(active_core: dict) -> list[dict]:
    active_rules = active_core.get("active_rules") or []
    selected = [rule for rule in active_rules if rule.get("id") in CORE_APPLICATION_RULE_IDS]
    if selected:
        return selected

    keywords = (
        "смысл",
        "утверж",
        "протокол",
        "инструк",
        "следующий шаг",
        "универсаль",
    )
    return [
        rule
        for rule in active_rules
        if _contains_any(" ".join(str(value) for value in rule.values()), keywords)
    ][: len(CORE_APPLICATION_RULE_IDS)]


def _select_applicable_stop_signals(active_core: dict) -> list[dict]:
    stop_signals = active_core.get("stop_signals") or []
    preferred_ids = {"STOP-UNKNOWN", "STOP-NO-AUTHORITY", "STOP-RULE-CONFLICT", "STOP-SYSTEM-BLOAT"}
    selected = [signal for signal in stop_signals if signal.get("id") in preferred_ids]
    return selected or stop_signals[:3]


def _required_moves(external_boris_request: bool) -> list[str]:
    moves = [
        "apply the Core Application Protocol before answering",
        "separate BOIS, SIMA, and BORIS roles",
        "make unknowns explicit",
        "present next steps as hypotheses, not facts",
    ]
    if external_boris_request:
        moves.extend(
            [
                "do not create a generic business plan",
                "explain how BOIS/SIMA/BORIS organizes the process",
                "treat the external domain as applied object, not primary expertise",
            ]
        )
    return moves


def _forbidden_moves(external_boris_request: bool) -> list[str]:
    moves = [
        "do not invent BOIS/SIMA/BORIS rules",
        "do not replace native BOIS Core rules with generic LLM reasoning",
        "do not hide uncertainty or scope boundaries",
    ]
    if external_boris_request:
        moves.extend(
            [
                "do not create a generic business plan",
                "do not act as a generic external-domain consultant",
                "do not present external-domain next steps as established facts",
            ]
        )
    return moves


def _scope_boundary(analysis: dict, external_boris_request: bool) -> str:
    if external_boris_request:
        return (
            "The external domain is an applied object. Answer only by showing how BOIS, SIMA, "
            "and BORIS organize the work; do not provide primary external-domain expertise."
        )
    if analysis.get("is_bois_related") or analysis.get("is_sima_related") or analysis.get("is_boris_related"):
        return "Answer inside BOIS/SIMA/BORIS scope using the loaded native BOIS Core context."
    return "If the request is outside BORIS Support scope, scope-limit or refuse according to the gate decision."


def _request_kind(analysis: dict, external_boris_request: bool) -> str:
    if external_boris_request:
        return "external_domain_with_boris_methodology"
    if analysis.get("is_bois_related"):
        return "bois_core_request"
    if analysis.get("is_sima_related"):
        return "sima_request"
    if analysis.get("is_boris_related"):
        return "boris_request"
    return analysis.get("domain", "unknown")


def _is_external_domain_with_boris(analysis: dict) -> bool:
    return bool(
        analysis.get("requires_domain_expertise")
        and (
            analysis.get("is_bois_related")
            or analysis.get("is_sima_related")
            or analysis.get("is_boris_related")
        )
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(needle in lower for needle in needles)
