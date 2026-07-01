from formatter import EMPTY_PRESENTATION, present_answer


def scaffold_llm_output(user_input: str, llm_output: str, parsed: dict | None = None) -> dict:
    parsed_input = parsed or {"raw": user_input, "intent": "general", "risk": 0.0, "uncertainty": 0.0}
    answer = present_answer(llm_output)
    if answer.strip() == user_input.strip():
        answer = EMPTY_PRESENTATION
    return {
        "input": parsed_input,
        "reasoning": {
            "raw": llm_output,
        },
        "bois": {
            "intent": parsed_input.get("intent", "general"),
            "risk": parsed_input.get("risk", 0.0),
            "uncertainty": parsed_input.get("uncertainty", 0.0),
            "route": "LLM",
        },
        "output": {
            "answer": answer,
            "key_points": _key_points(answer),
        },
    }


def _key_points(answer: str) -> list:
    points = []
    for line in answer.splitlines():
        cleaned = line.strip(" -•\t")
        if cleaned:
            points.append(cleaned)
    return points[:5] if len(points) > 1 else []
