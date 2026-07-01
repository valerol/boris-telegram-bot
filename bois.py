import json
from cognitive_scaffold import scaffold_llm_output
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

    return scaffold_llm_output(user_text, llm_response)
