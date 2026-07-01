import json
import ast
import re


PREFERRED_TEXT_KEYS = (
    "output.answer",
    "answer",
    "conclusion",
    "response.description",
    "response",
    "summary",
    "description",
    "definition",
    "message",
    "text",
    "content",
)

EMPTY_PRESENTATION = "I could not produce a clean answer from the model output."
BLOCKED_FALLBACKS = (
    "input processed successfully.",
)


def render_boris_response(contract: dict) -> str:
    scope_status = contract.get("scope_status", "unclear")
    if scope_status == "out_of_scope":
        return _render_boundary(contract)
    if scope_status in {"unclear", "invalid_input"}:
        return _render_clarification(contract)
    return _render_in_scope(contract)


def _render_in_scope(contract: dict) -> str:
    sections = [
        ("BOIS", contract.get("bois_section")),
        ("SIMA", contract.get("sima_section")),
        ("BORIS", contract.get("boris_section")),
    ]
    lines = []
    direct_answer = _clean_contract_text(contract.get("direct_answer"))
    if direct_answer:
        lines.append(direct_answer)
        lines.append("")

    for title, value in sections:
        cleaned = _clean_contract_text(value)
        if cleaned:
            lines.append(f"{title}: {cleaned}")

    boundary = _clean_contract_text(contract.get("boundary_note"))
    if boundary:
        lines.append(f"Граница: {boundary}")

    next_step = _clean_contract_text(contract.get("next_step"))
    if next_step:
        lines.append(f"Следующий шаг: {next_step}")

    return "\n".join(lines).strip() or EMPTY_PRESENTATION


def _render_boundary(contract: dict) -> str:
    boundary = _clean_contract_text(contract.get("boundary_note"))
    if not boundary:
        boundary = "Этот запрос выходит за пределы BORIS Support."
    next_step = _clean_contract_text(contract.get("next_step"))
    if next_step:
        return f"{boundary}\n\nСледующий шаг: {next_step}"
    return boundary


def _render_clarification(contract: dict) -> str:
    boundary = _clean_contract_text(contract.get("boundary_note"))
    if not boundary:
        boundary = "Запрос нужно уточнить, чтобы ответить в рамках BORIS Support."
    missing = contract.get("missing_info") or []
    next_step = _clean_contract_text(contract.get("next_step"))
    lines = [boundary]
    if missing:
        lines.append("Не хватает: " + ", ".join(str(item) for item in missing))
    if next_step:
        lines.append("Следующий шаг: " + next_step)
    return "\n".join(lines).strip()


def _clean_contract_text(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def present_answer(raw_llm_output: str) -> str:
    print("PRESENTATION_INPUT")
    text = _normalize_text(raw_llm_output)
    parsed = _parse_structured_text(text)

    if parsed is None:
        answer = _clean_plain_text(text)
    else:
        answer = _extract_user_text(parsed)

    answer = _clean_plain_text(answer)
    if not answer or _is_blocked_fallback(answer) or _looks_like_raw_object(answer):
        answer = EMPTY_PRESENTATION

    print("PRESENTATION_OUTPUT_READY")
    return answer


def _normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _clean_plain_text(text):
    text = _normalize_text(text)
    text = _strip_code_fence(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_structured_text(text):
    stripped = _strip_code_fence(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    try:
        parsed = ast.literal_eval(stripped)
    except (ValueError, SyntaxError):
        return None
    return parsed if isinstance(parsed, (dict, list, str)) else None


def _strip_code_fence(text):
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_user_text(value):
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = [_extract_user_text(item) for item in value]
        return "\n".join(part for part in parts if part)

    if not isinstance(value, dict):
        return ""

    if "analysis" in value and "conclusion" in value:
        conclusion = _extract_user_text(value["conclusion"])
        if conclusion:
            return conclusion

    for key_path in PREFERRED_TEXT_KEYS:
        extracted = _extract_key_path(value, key_path)
        if extracted:
            return extracted

    response = value.get("response")
    if isinstance(response, dict):
        extracted = _extract_user_text(response)
        if extracted:
            return extracted

    return _compact_points(value)


def _extract_key_path(value, key_path):
    current = value
    for key in key_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return ""
        current = current[key]
    return _extract_user_text(current)


def _compact_points(value):
    points = []
    for key, item in value.items():
        if key == "analysis":
            continue
        if isinstance(item, str):
            points.append(f"{_label(key)}: {item}")
        elif isinstance(item, (int, float)):
            points.append(f"{_label(key)}: {item}")
        elif isinstance(item, list):
            scalars = [str(entry) for entry in item if isinstance(entry, (str, int, float))]
            if scalars:
                points.append(f"{_label(key)}: {', '.join(scalars)}")
    return "\n".join(points[:5])


def _label(key):
    return str(key).replace("_", " ").strip().capitalize()


def _is_blocked_fallback(answer):
    lower = answer.strip().lower()
    if lower in BLOCKED_FALLBACKS:
        return True
    if lower.startswith("intent:") and "risk" in lower and "uncertainty" in lower:
        return True
    if lower.startswith("intent:") or lower.startswith("risk level:"):
        return True
    return False


def _looks_like_raw_object(answer):
    stripped = answer.strip()
    return (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]"))
