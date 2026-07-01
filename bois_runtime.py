import json

from bois_context import BOIS_CONTEXT
from cognitive_scaffold import scaffold_llm_output
from llm import call_llm
from parser import parse


LLM_ERROR_MESSAGE = "LLM call failed. Please check OPENAI_API_KEY and runtime logs."


class BOISRuntime:

    def run(self, text: str) -> dict:
        print("BOIS_RUNTIME_START")
        parsed = parse(text)
        prompt = self._build_prompt(text, parsed)

        try:
            raw_llm_output = call_llm(prompt)
        except Exception:
            return self._llm_error_output(parsed)

        result = scaffold_llm_output(text, raw_llm_output)
        result["input"] = parsed
        result["bois"]["intent"] = parsed.get("intent", result["bois"]["intent"])
        result["bois"]["risk"] = parsed.get("risk", result["bois"]["risk"])
        result["bois"]["uncertainty"] = parsed.get("uncertainty", result["bois"]["uncertainty"])
        result["bois"]["route"] = "LLM"
        return result

    def _build_prompt(self, text: str, parsed: dict) -> str:
        return f"""{BOIS_CONTEXT}

User request:
{text}

Parsed runtime context:
{json.dumps(parsed, ensure_ascii=False, indent=2)}

Think freely and answer the user's request usefully.
Use the BOIS/SIMA/BORIS context when the user asks about BOIS, SIMA, BORIS, or this assistant.
Do not return raw JSON, schemas, or internal runtime dumps unless the user explicitly asks for them.
"""

    def _llm_error_output(self, parsed: dict) -> dict:
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
