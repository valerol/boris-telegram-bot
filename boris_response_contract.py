from __future__ import annotations

import json


SCOPE_STATUSES = {"in_scope", "out_of_scope", "unclear", "invalid_input"}
REQUIRED_FIELDS = (
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


def parse_response_contract(raw_output: str) -> tuple[dict | None, list[str]]:
    try:
        parsed = json.loads(raw_output)
    except (TypeError, json.JSONDecodeError) as error:
        return None, [f"Invalid JSON response contract: {error}"]
    return validate_response_contract(parsed)


def validate_response_contract(value) -> tuple[dict | None, list[str]]:
    if not isinstance(value, dict):
        return None, ["Response contract must be a JSON object"]

    errors = []
    for field in REQUIRED_FIELDS:
        if field not in value:
            errors.append(f"Missing response contract field: {field}")

    if errors:
        return None, errors

    contract = dict(value)
    if contract["scope_status"] not in SCOPE_STATUSES:
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
        if contract[field] is None:
            contract[field] = ""
        if not isinstance(contract[field], str):
            errors.append(f"Response contract field must be a string: {field}")

    if not isinstance(contract["missing_info"], list):
        errors.append("Response contract field must be a list: missing_info")
    else:
        contract["missing_info"] = [str(item) for item in contract["missing_info"]]

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
    missing_info = list(analysis.get("missing_info", []))
    if errors:
        missing_info.append("valid_response_contract")
    return {
        "scope_status": "unclear",
        "request_type": analysis.get("requested_operation", analysis.get("intent", "general_request")),
        "primary_domain": "boris_support",
        "applied_domain": analysis.get("domain", "unknown"),
        "bois_section": "",
        "sima_section": "Ответ модели не прошел структурную проверку контракта.",
        "boris_section": "",
        "direct_answer": "",
        "boundary_note": "Я не могу отправить сырой или неструктурированный ответ модели.",
        "next_step": "Переформулируйте запрос или повторите попытку.",
        "confidence": 0.2,
        "missing_info": missing_info,
    }
