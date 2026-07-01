import json
import re


TEXT_KEYS = (
    "answer",
    "conclusion",
    "summary",
    "description",
    "message",
    "text",
    "content",
)


def scaffold_llm_output(user_input: str, llm_output: str) -> dict:
    answer = _clean_answer(llm_output)
    return {
        "input": {
            "text": user_input,
        },
        "reasoning": {
            "raw": llm_output,
        },
        "bois": {
            "intent": _intent(user_input),
            "risk": _risk(user_input, llm_output),
            "uncertainty": _uncertainty(user_input),
            "route": "LLM",
        },
        "output": {
            "answer": answer,
            "key_points": _key_points(answer),
        },
    }


def _clean_answer(llm_output: str) -> str:
    text = str(llm_output).strip()
    if not text:
        return "Не удалось получить ответ."

    parsed = _parse_json(text)
    if parsed is None:
        return text

    extracted = _extract_text(parsed)
    return extracted.strip() if extracted else text


def _parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_text(value) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = [_extract_text(item) for item in value]
        return "\n".join(part for part in parts if part)

    if not isinstance(value, dict):
        return ""

    for key in TEXT_KEYS:
        if key in value:
            extracted = _extract_text(value[key])
            if extracted:
                return extracted

    response = value.get("response")
    if isinstance(response, dict):
        extracted = _extract_text(response)
        if extracted:
            return extracted

    return _compact_dict(value)


def _compact_dict(value: dict) -> str:
    points = []
    for key, item in value.items():
        if isinstance(item, (str, int, float)):
            points.append(f"{_label(key)}: {item}")
        elif isinstance(item, list):
            scalars = [str(entry) for entry in item if isinstance(entry, (str, int, float))]
            if scalars:
                points.append(f"{_label(key)}: {', '.join(scalars)}")
    return "\n".join(points[:5])


def _intent(user_input: str) -> str:
    text = user_input.lower()
    if any(marker in text for marker in ("?", "what", "что", "как", "why", "почему")):
        return "question"
    if any(marker in text for marker in ("create", "make", "write", "создай", "сделай", "напиши")):
        return "creation"
    if any(marker in text for marker in ("compare", "choose", "лучше", "выбери", "сравни")):
        return "decision"
    if any(marker in text for marker in ("explain", "tell", "объясни", "расскажи")):
        return "explanation"
    return "general"


def _risk(user_input: str, llm_output: str) -> float:
    text = f"{user_input} {llm_output}".lower()
    high_markers = ("hack", "steal", "exploit", "fraud", "bomb", "наркотик", "взлом")
    medium_markers = ("medical", "legal", "finance", "полит", "война", "здоров", "деньги")
    if any(marker in text for marker in high_markers):
        return 0.8
    if any(marker in text for marker in medium_markers):
        return 0.45
    return 0.1


def _uncertainty(user_input: str) -> float:
    words = re.findall(r"\w+", user_input.lower())
    if len(words) <= 2:
        return 0.6
    if any(marker in user_input.lower() for marker in ("maybe", "может", "примерно", "не знаю")):
        return 0.55
    return 0.25


def _key_points(answer: str) -> list:
    points = []
    for line in answer.splitlines():
        cleaned = line.strip(" -•\t")
        if cleaned:
            points.append(cleaned)
    return points[:5] if len(points) > 1 else []


def _label(key) -> str:
    return str(key).replace("_", " ").strip().capitalize()
