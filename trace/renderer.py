from __future__ import annotations

from boris.engine import ReasoningFrame
from sima.engine import IntentAnalysis

INTENT_SUMMARIES = {
    "question": "The request is a question that needs a direct answer.",
    "creation": "The request asks for new content to be drafted.",
    "revision": "The request asks for existing material to be improved.",
    "decision": "The request asks for options to be weighed.",
    "general": "The request is open-ended and needs a direct response.",
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
Intent: {sima["intent"]}

🧠 How I analyzed it
Ops: {", ".join(str(oper) for oper in sima["opers"])}
Uncertainty: {sima["uncertainty"]}

⚙️ How I decided to proceed
Risk: {bois["risk"]}
Constraints: {", ".join(str(constraint) for constraint in boris["constraints"])}

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
            "I can help with this, but I need to keep the answer general because the available context is limited.",
            gate,
        )

    def _understood(self, analysis: IntentAnalysis) -> str:
        return INTENT_SUMMARIES.get(analysis.intent, INTENT_SUMMARIES["general"])

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
