from boris_domain import (
    is_bois_related,
    is_boris_related,
    is_methodology_request,
    is_sima_related,
    resolve_domain,
)


def parse(user_text: str) -> dict:
    lower = user_text.lower()
    domain = resolve_domain(user_text)
    requested_operation = _requested_operation(lower, domain)
    intent_type = _intent_type(lower, requested_operation)
    missing_info = _missing_info(lower, domain)
    uncertainty = _uncertainty(user_text, missing_info)
    risk_level = _risk_level(domain)
    bois_related = is_bois_related(lower)
    sima_related = is_sima_related(lower)
    boris_related = is_boris_related(lower)
    target_object = _target_object(lower)
    requires_domain_expertise = domain.endswith("_generic") or target_object in {"business_plan"}
    allow_candidate = bois_related or sima_related or boris_related or domain in {
        "bois_boris_methodology",
        "bois_boris_implementation",
        "llm_integration",
        "application_architecture",
        "personal_thinking",
    }

    return {
        "raw": user_text,
        "intent": intent_type,
        "risk": _risk_score(risk_level),
        "uncertainty": uncertainty,
        "raw_user_text": user_text,
        "intent_type": intent_type,
        "domain": domain,
        "requested_operation": requested_operation,
        "target_object": target_object,
        "requires_domain_expertise": requires_domain_expertise,
        "is_bois_related": bois_related,
        "is_sima_related": sima_related,
        "is_boris_related": boris_related,
        "missing_info": missing_info,
        "risk_level": risk_level,
        "allow_candidate": allow_candidate,
        "reason": _reason(domain, allow_candidate, is_methodology_request(lower)),
    }


def _requested_operation(text: str, domain: str) -> str:
    if "бизнес-план" in text or "business plan" in text:
        return "apply_methodology" if _has_boris_scope(text) else "create_business_plan"
    if "рецепт" in text or "recipe" in text:
        return "write_recipe"
    if "проанализ" in text or "analyze" in text:
        if "sima" in text or "сима" in text:
            return "analyze_through_sima"
        return "analyze_through_bois" if _has_boris_scope(text) else "generic_analysis"
    if "архитект" in text or "architecture" in text:
        return "design_boris_runtime" if _has_boris_scope(text) else "generic_architecture"
    if "реализ" in text or "implement" in text:
        return "integrate_with_application" if _has_boris_scope(text) else "generic_programming"
    if "интегр" in text or "llm" in text:
        return "integrate_with_llm" if _has_boris_scope(text) else "generic_programming"
    if domain in {"bois_core", "sima_analysis", "boris_runtime", "boris_protocol"}:
        return f"explain_{domain.split('_')[0]}"
    return "general_request"


def _intent_type(text: str, requested_operation: str) -> str:
    if requested_operation.startswith("create") or requested_operation.startswith("write"):
        return "creation"
    if requested_operation.startswith("analyze"):
        return "analysis"
    if requested_operation.startswith("design") or requested_operation.startswith("integrate"):
        return "implementation"
    if "?" in text or text.startswith(("как", "что", "why", "how", "what")):
        return "question"
    return "general"


def _target_object(text: str) -> str:
    if "бизнес-план" in text or "business plan" in text:
        return "business_plan"
    if "telegram" in text or "бот" in text or "bot" in text:
        return "telegram_bot"
    if "saas" in text:
        return "saas"
    if "ответ" in text or "response" in text:
        return "response"
    return "unspecified"


def _missing_info(text: str, domain: str) -> list[str]:
    missing = []
    if domain == "unknown" and len(text.split()) < 4:
        missing.append("scope")
    return missing


def _uncertainty(text: str, missing_info: list[str]) -> float:
    score = 0.2
    if len(text.split()) < 4:
        score += 0.2
    if missing_info:
        score += 0.2
    return min(round(score, 2), 1.0)


def _risk_level(domain: str) -> str:
    if domain in {"medical_generic", "legal_generic", "finance_generic"}:
        return "high"
    if domain.endswith("_generic"):
        return "medium"
    return "low"


def _risk_score(risk_level: str) -> float:
    return {"low": 0.1, "medium": 0.45, "high": 0.8}.get(risk_level, 0.1)


def _reason(domain: str, allow_candidate: bool, methodology_request: bool) -> str:
    if allow_candidate:
        return "bois_sima_boris_scope"
    if methodology_request:
        return "external_domain_methodology_candidate"
    if domain.endswith("_generic"):
        return "external_domain_without_boris_scope"
    return "unclear_scope"


def _has_boris_scope(text: str) -> bool:
    return any(marker in text for marker in ("bois", "боис", "sima", "сима", "boris", "борис"))
