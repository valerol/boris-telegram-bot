import json
from cognitive_scaffold import scaffold_llm_output
from parser import parse
from llm import call_llm

LLM_ERROR_MESSAGE = "LLM call failed. Please check OPENAI_API_KEY and runtime logs."

def build_prompt(parsed):
    return f"""BOIS v0.1 CONTEXT

INPUT:
{json.dumps(parsed, ensure_ascii=False, indent=2)}

Return structured response only.
"""

def run(user_text: str):
    parsed = parse(user_text)
    prompt = build_prompt(parsed)
    try:
        llm_response = call_llm(prompt)
    except Exception:
        return _llm_error_output(parsed)

    result = scaffold_llm_output(user_text, llm_response)
    result["input"] = parsed
    result["bois"]["intent"] = parsed.get("intent", result["bois"]["intent"])
    result["bois"]["risk"] = parsed.get("risk", result["bois"]["risk"])
    result["bois"]["uncertainty"] = parsed.get("uncertainty", result["bois"]["uncertainty"])
    result["bois"]["route"] = "LLM"
    return result


def _llm_error_output(parsed):
    return {
        "input": parsed,
        "bois": {
            "intent": parsed.get("intent", "general"),
            "risk": parsed.get("risk", 0.0),
            "uncertainty": parsed.get("uncertainty", 0.0),
            "route": "LLM",
        },
        "reasoning": {
            "raw": "",
        },
        "output": {
            "answer": LLM_ERROR_MESSAGE,
            "key_points": [],
        },
    }
