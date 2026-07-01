from __future__ import annotations

from boris.engine import ReasoningFrame
from sima.engine import IntentAnalysis

INTENT_SUMMARIES = {
    "question": "Intent class: question.",
    "explanation_request": "Intent class: explanation_request.",
    "creation_request": "Intent class: creation_request.",
    "decision_request": "Intent class: decision_request.",
    "system_query": "Intent class: system_query.",
}


def render_trace(
    text: str,
    bois: dict[str, object],
    sima: dict[str, object],
    boris: dict[str, object],
    answer: str,
) -> str:
    return f"""
🧭 What I understood
{INTENT_SUMMARIES.get(str(sima["intent"]), INTENT_SUMMARIES["explanation_request"])}

🧠 How I analyzed it
- intent: {sima["intent"]}
- opers: {", ".join(str(oper) for oper in sima["opers"])}
- uncertainty: {sima["uncertainty"]}
- missing_info: {", ".join(str(field) for field in sima["missing_info"]) or "none"}

⚙️ How I decided to proceed
- gate: {"allowed" if bois["allowed"] else "blocked"}
- risk: {bois["risk"]}
- constraints: {", ".join(str(constraint) for constraint in boris["constraints"])}

💬 Answer
{answer}
""".strip()


class HumanTraceRenderer:
    """Deterministic renderer with no external calls."""

    def render(
        self,
        analysis: IntentAnalysis,
        frame: ReasoningFrame,
        answer: str,
        gate: dict[str, object] | None = None,
    ) -> str:
        clean_answer = self._clean(answer)
        return render_trace(
            "",
            gate or {"allowed": True, "reason": "ok", "risk": "low"},
            analysis.to_dict(),
            frame.to_dict(),
            clean_answer,
        )

    def fallback(
        self,
        analysis: IntentAnalysis,
        frame: ReasoningFrame,
        gate: dict[str, object] | None = None,
    ) -> str:
        return self.render(
            analysis,
            frame,
            "Answer unavailable.",
            gate,
        )

    def _understood(self, analysis: IntentAnalysis) -> str:
        return INTENT_SUMMARIES.get(analysis.intent, INTENT_SUMMARIES["explanation_request"])

    def _analysis(self, analysis: IntentAnalysis) -> str:
        missing = ", ".join(analysis.missing_info) if analysis.missing_info else "none"
        ops = "\n".join(f"- {oper}" for oper in analysis.opers) or "- none"
        return "\n".join(
            [
                "- operations:",
                ops,
                f"- uncertainty: {analysis.uncertainty:.2f}",
                f"- missing info: {missing}",
            ]
        )

    def _decision(self, frame: ReasoningFrame, gate: dict[str, object] | None) -> str:
        allowed = gate.get("allowed", True) if gate else True
        risk = str(gate.get("risk", "low")) if gate else "low"
        state = "allowed" if allowed else "blocked"
        constraints = ", ".join(frame.constraints) if frame.constraints else "none"
        return "\n".join(
            [
                f"- gate: {state}",
                f"- risk: {risk}",
                f"- domain: {frame.domain}",
                f"- constraints: {constraints}",
            ]
        )

    def _clean(self, answer: str) -> str:
        cleaned = answer.strip()
        for heading in (
            "🧭 What I understood",
            "🧠 How I analyzed it",
            "⚙️ How I decided to proceed",
            "💬 Answer",
        ):
            cleaned = cleaned.replace(heading, "").strip()
        return cleaned or "I do not have enough information to answer confidently."
