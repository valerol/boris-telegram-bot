from __future__ import annotations

import json


SCOPE_STATUSES = {"in_scope", "out_of_scope", "unclear", "invalid_input"}
EMERGENCY_REQUIRED_FIELDS = (
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
)
REQUIRED_FIELDS = EMERGENCY_REQUIRED_FIELDS
TEXT_FIELD_CANDIDATES = ("answer", "text", "content", "response", "summary", "message")


def parse_response_contract(raw_output: str, extracted_contract=None, analysis: dict | None = None) -> tuple[dict | None, list[str]]:
    try:
        parsed = json.loads(raw_output)
    except (TypeError, json.JSONDecodeError) as error:
        print(f"CONTRACT_PARSE_FAILED: {error}")
        return None, [f"Invalid JSON response contract: {error}"]
    normalized = normalize_response_contract(parsed, analysis or {}, extracted_contract)
    if normalized != parsed:
        print("CONTRACT_NORMALIZED")
    contract, errors = validate_response_contract(normalized, extracted_contract)
    if errors:
        print(f"CONTRACT_VALIDATION_FAILED: {errors}")
    return contract, errors


def normalize_response_contract(value, analysis: dict, extracted_contract=None) -> dict:
    base = deterministic_contract(analysis, _scope_from_analysis(analysis), "", "")
    if not isinstance(value, dict):
        return base

    normalized = dict(base)
    for field in _required_fields(extracted_contract):
        if field in value:
            normalized[field] = value[field]

    if not normalized.get("direct_answer"):
        text = _extract_text_field(value)
        if text:
            normalized["direct_answer"] = text

    return normalized


def validate_response_contract(value, extracted_contract=None) -> tuple[dict | None, list[str]]:
    if not isinstance(value, dict):
        return None, ["Response contract must be a JSON object"]

    errors = []
    for field in _required_fields(extracted_contract):
        if field not in value:
            errors.append(f"Missing response contract field: {field}")

    if errors:
        return None, errors

    contract = dict(value)
    if "scope_status" in contract and contract["scope_status"] not in SCOPE_STATUSES:
        errors.append("Invalid response contract field: scope_status")

    for field in (
        "request_type",
        "primary_domain",
        "applied_domain",
        "bois_section",
        "sima_section",
        "boris_section",
        "direct_answer",
        "boundary_note",
        "next_step",
    ):
        if field not in contract:
            continue
        if contract[field] is None:
            contract[field] = ""
        if not isinstance(contract[field], str):
            errors.append(f"Response contract field must be a string: {field}")

    if "missing_info" in contract and not isinstance(contract["missing_info"], list):
        errors.append("Response contract field must be a list: missing_info")
    elif "missing_info" in contract:
        contract["missing_info"] = [str(item) for item in contract["missing_info"]]

    if "confidence" in contract:
        try:
            contract["confidence"] = float(contract["confidence"])
        except (TypeError, ValueError):
            errors.append("Response contract field must be numeric: confidence")
        else:
            contract["confidence"] = max(0.0, min(contract["confidence"], 1.0))

    if errors:
        return None, errors
    return contract, []


def deterministic_contract(analysis: dict, scope_status: str, boundary_note: str, direct_answer: str = "") -> dict:
    return {
        "scope_status": scope_status,
        "request_type": analysis.get("requested_operation", analysis.get("intent", "general_request")),
        "primary_domain": "boris_support",
        "applied_domain": analysis.get("domain", "unknown"),
        "bois_section": "",
        "sima_section": "",
        "boris_section": "",
        "direct_answer": direct_answer,
        "boundary_note": boundary_note,
        "next_step": "Уточните запрос в рамках BOIS/SIMA/BORIS." if scope_status != "out_of_scope" else "",
        "confidence": 0.7,
        "missing_info": analysis.get("missing_info", []),
    }


def fallback_contract(analysis: dict, errors: list[str] | None = None) -> dict:
    scope_status = _scope_from_analysis(analysis)
    if scope_status == "out_of_scope":
        return deterministic_contract(
            analysis,
            "out_of_scope",
            "Этот запрос выходит за пределы BORIS Support.",
        )
    if scope_status in {"unclear", "invalid_input"}:
        return deterministic_contract(
            analysis,
            scope_status,
            "Запрос нужно уточнить, чтобы ответить в рамках BORIS Support.",
        )
    return {
        "scope_status": "in_scope",
        "request_type": analysis.get("requested_operation", analysis.get("intent", "general_request")),
        "primary_domain": "boris_support",
        "applied_domain": analysis.get("domain", "unknown"),
        "bois_section": "Зафиксировать объект и смысл запроса.",
        "sima_section": "Восстановить известное, неизвестное и границы.",
        "boris_section": "Организовать следующий шаг в рамках протокола.",
        "direct_answer": (
            "Запрос относится к области BORIS Support, но модель не вернула корректную структуру ответа. "
            "Я могу ответить только в структурированном формате BOIS/SIMA/BORIS."
        ),
        "boundary_note": "",
        "next_step": "Повторите запрос или уточните, какой аспект BOIS/SIMA/BORIS нужно разобрать.",
        "confidence": 0.3,
        "missing_info": list(analysis.get("missing_info", [])),
    }


def _required_fields(extracted_contract=None) -> tuple[str, ...]:
    if extracted_contract is not None and getattr(extracted_contract, "available", False):
        fields = tuple(getattr(extracted_contract, "output_field_names", []) or ())
        if fields:
            return fields
    if isinstance(extracted_contract, dict) and extracted_contract.get("extraction_status") in {"complete", "partial"}:
        fields = tuple(
            field.get("name")
            for field in extracted_contract.get("required_output_fields", [])
            if isinstance(field, dict) and field.get("name")
        )
        if fields:
            return fields
    return EMERGENCY_REQUIRED_FIELDS


def _extract_text_field(value: dict) -> str:
    for field in TEXT_FIELD_CANDIDATES:
        item = value.get(field)
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, dict):
            nested = _extract_text_field(item)
            if nested:
                return nested
    return ""


def _scope_from_analysis(analysis: dict) -> str:
    decision = (analysis.get("gate") or {}).get("decision")
    if decision == "DENY_OUT_OF_SCOPE":
        return "out_of_scope"
    if decision == "CLARIFY":
        return "unclear"
    if not str(analysis.get("raw_user_text") or analysis.get("raw") or "").strip():
        return "invalid_input"
    return "in_scope"
