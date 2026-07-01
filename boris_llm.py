import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from boris_identity import identity_payload
from boris_response_contract import REQUIRED_FIELDS

load_dotenv()

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)

def build_llm_prompt(user_text: str, analysis: dict, gate_decision: dict) -> str:
    sima_analysis = _analysis_without_core_payloads(analysis)
    return f"""BORIS Support identity:
{json.dumps(identity_payload(), ensure_ascii=False, indent=2)}

Core Application Protocol:
{json.dumps(analysis.get("core_application_protocol", {}), ensure_ascii=False, indent=2)}

SIMA analysis:
{json.dumps(sima_analysis, ensure_ascii=False, indent=2)}

Capability gate decision:
{json.dumps(gate_decision, ensure_ascii=False, indent=2)}

Relevant Native BOIS Core context:
{json.dumps(analysis.get("active_core", {}), ensure_ascii=False, indent=2)}

User request:
{user_text}

You are BORIS Support.
Apply the Core Application Protocol before answering.
The loaded native BOIS Core is the canonical source for BOIS/SIMA/BORIS knowledge.
Do not invent BOIS/SIMA/BORIS rules.
Do not reconstruct missing BOIS/SIMA/BORIS concepts from memory.
Answer only within BORIS Support scope.
If the gate decision limits scope, stay within BOIS/SIMA/BORIS methodology and do not perform generic expert work in the external domain.
For external-domain-with-BORIS requests, explain through BOIS/SIMA/BORIS instead of becoming a generic external-domain consultant.
Refuse or scope-limit if the Core Application Protocol or gate decision requires it.
Before finalizing, run this self-check: Did I answer as BORIS Support, or did I become a generic consultant?
Return strict JSON only. Do not write the final Telegram message.
The JSON object must contain exactly these response contract fields:
{json.dumps(list(REQUIRED_FIELDS), ensure_ascii=False)}
Allowed scope_status values: in_scope, out_of_scope, unclear, invalid_input.
Fill bois_section, sima_section, boris_section, direct_answer, boundary_note, and next_step as data fields.
"""


def _analysis_without_core_payloads(analysis: dict) -> dict:
    compact = dict(analysis)
    active_core = compact.get("active_core") or {}
    if active_core:
        compact["active_core"] = {
            "available": active_core.get("available"),
            "version": active_core.get("version"),
            "validation_status": active_core.get("validation_status"),
            "identity": active_core.get("identity"),
        }
    protocol = compact.get("core_application_protocol") or {}
    if protocol:
        compact["core_application_protocol"] = {
            "present": True,
            "request_kind": protocol.get("request_kind"),
            "applicable_rules_count": len(protocol.get("applicable_rules") or []),
            "forbidden_moves_count": len(protocol.get("forbidden_answer_moves") or []),
        }
    return compact


def call_llm(prompt: str):
    print("LLM_CALL_START")
    try:
        client = get_client()

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are BORIS Support. "
                        "Use the loaded native BOIS Core as the canonical source for BOIS/SIMA/BORIS knowledge. "
                        "Do not invent BOIS/SIMA/BORIS rules. "
                        "Stay within BORIS Support scope. "
                        "Return only a valid JSON object that matches the BORIS response contract."
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
