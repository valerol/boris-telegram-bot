import json


PREFERRED_TEXT_KEYS = (
    "answer",
    "conclusion",
    "summary",
    "description",
    "message",
    "text",
    "content",
)


def format_response(runtime_output):
    output = runtime_output.get("output", {}) if isinstance(runtime_output, dict) else {}
    answer = output.get("answer", "")
    return _clean_answer(answer)


def _clean_answer(answer):
    if not isinstance(answer, str):
        return str(answer)

    text = answer.strip()
    if not text:
        return "Не удалось получить ответ."

    parsed = _parse_json(text)
    if parsed is None:
        return text

    extracted = _extract_user_text(parsed)
    return extracted.strip() if extracted else text


def _parse_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_user_text(value):
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = [_extract_user_text(item) for item in value]
        return "\n".join(part for part in parts if part)

    if not isinstance(value, dict):
        return ""

    for key in PREFERRED_TEXT_KEYS:
        if key in value:
            extracted = _extract_user_text(value[key])
            if extracted:
                return extracted

    response = value.get("response")
    if isinstance(response, dict):
        extracted = _extract_user_text(response)
        if extracted:
            return extracted

    return _compact_points(value)


def _compact_points(value):
    points = []
    for key, item in value.items():
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
