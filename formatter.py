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


def format_response(runtime_output):
    output = runtime_output.get("output", {}) if isinstance(runtime_output, dict) else {}
    answer = output.get("answer", "")
    return present_answer(answer)


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


def _clean_answer(answer):
    return present_answer(answer)


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
