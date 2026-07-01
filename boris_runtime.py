from boris_domain import resolve_domain
from boris_gate import ALLOW_WITH_SCOPE_LIMIT, CLARIFY, DENY_OUT_OF_SCOPE, decide_capability
from boris_llm import build_llm_prompt, call_llm
from boris_protocol import scaffold_llm_output
from boris_templates import CLARIFY_RU, OUT_OF_SCOPE_RU, SCOPE_LIMIT_PREFIX_RU
from sima_analyzer import parse


LLM_ERROR_MESSAGE = "LLM call failed. Please check OPENAI_API_KEY and runtime logs."


class BOISRuntime:
    def __init__(self, llm_call=call_llm) -> None:
        self._llm_call = llm_call

    def run(self, text: str) -> dict:
        print("BOIS_RUNTIME_START")
        analysis = parse(text)
        domain = resolve_domain(text)
        analysis["domain"] = domain
        gate_decision = decide_capability(analysis, domain)
        analysis["gate"] = gate_decision.to_dict()

        if gate_decision.decision == DENY_OUT_OF_SCOPE:
            return scaffold_llm_output(text, OUT_OF_SCOPE_RU, analysis)

        if gate_decision.decision == CLARIFY:
            return scaffold_llm_output(text, CLARIFY_RU, analysis)

        prompt = build_llm_prompt(text, analysis, gate_decision.to_dict())

        try:
            raw_llm_output = self._llm_call(prompt)
        except Exception:
            return self._llm_error_output(analysis)

        if gate_decision.decision == ALLOW_WITH_SCOPE_LIMIT:
            raw_llm_output = f"{SCOPE_LIMIT_PREFIX_RU}\n\n{raw_llm_output}"

        return scaffold_llm_output(text, raw_llm_output, analysis)

    def _llm_error_output(self, analysis: dict) -> dict:
        return {
            "input": analysis,
            "bois": {
                "intent": analysis.get("intent", "general"),
                "risk": analysis.get("risk", 0.0),
                "uncertainty": analysis.get("uncertainty", 0.0),
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
