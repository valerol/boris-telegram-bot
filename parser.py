def parse(user_text: str):
    intent = "general"
    t = user_text.lower()

    if "what is" in t:
        intent = "explanation"
    if "how" in t:
        intent = "instruction"

    return {
        "raw": user_text,
        "intent": intent,
        "risk": 0.1,
        "uncertainty": 0.4
    }
