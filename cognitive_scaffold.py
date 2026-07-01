import re

from formatter import EMPTY_PRESENTATION, present_answer


def scaffold_llm_output(user_input: str, llm_output: str) -> dict:
    answer = present_answer(llm_output)
    if answer.strip() == user_input.strip():
        answer = EMPTY_PRESENTATION
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
