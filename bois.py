import json
from parser import parse
from llm import call_llm

def build_prompt(parsed):
    return f"""BOIS v0.1 CONTEXT

INPUT:
{json.dumps(parsed, ensure_ascii=False, indent=2)}

Return structured response only.
"""

def run(user_text: str):
    parsed = parse(user_text)
    prompt = build_prompt(parsed)
    llm_response = call_llm(prompt)

    return {
        "bois_version": "0.1",
        "input": parsed,
        "decision": {
            "route": "LLM",
            "reason": "default"
        },
        "llm": {
            "prompt": prompt,
            "response_raw": llm_response
        },
        "output": {
            "summary": llm_response[:200],
            "answer": llm_response,
            "notes": []
        }
    }
