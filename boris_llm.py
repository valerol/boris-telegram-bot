import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from boris_identity import identity_payload

load_dotenv()

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)

def build_llm_prompt(user_text: str, analysis: dict, gate_decision: dict) -> str:
    return f"""BORIS Support identity:
{json.dumps(identity_payload(), ensure_ascii=False, indent=2)}

Native BOIS Core context:
{json.dumps(analysis.get("active_core", {}), ensure_ascii=False, indent=2)}

SIMA analysis:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Capability gate decision:
{json.dumps(gate_decision, ensure_ascii=False, indent=2)}

User request:
{user_text}

You are BORIS Support.
The loaded native BOIS Core is the canonical source for BOIS/SIMA/BORIS knowledge.
Do not invent BOIS/SIMA/BORIS rules.
Do not reconstruct missing BOIS/SIMA/BORIS concepts from memory.
Answer only within BORIS Support scope.
If the gate decision limits scope, stay within BOIS/SIMA/BORIS methodology and do not perform generic expert work in the external domain.
Do not expose internal runtime fields or raw JSON unless the user explicitly asks for that format.
"""


def call_llm(prompt: str):
    print("LLM_CALL_START")
    try:
        client = get_client()

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are BORIS Support. "
                        "Use the loaded native BOIS Core as the canonical source for BOIS/SIMA/BORIS knowledge. "
                        "Do not invent BOIS/SIMA/BORIS rules. "
                        "Stay within BORIS Support scope. "
                        "Do not expose internal runtime fields or raw JSON unless the user explicitly asks for that format."
                    ),
                },
                {"role": "user", "content": prompt}
            ]
        )

        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("empty LLM response")
        print("LLM_CALL_OK")
        return content
    except Exception as error:
        print(f"LLM_CALL_ERROR: {error}")
        raise
