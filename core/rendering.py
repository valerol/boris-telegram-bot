from __future__ import annotations

from boris.structurer import ReasoningFrame
from sima.analyzer import IntentAnalysis


class HumanTraceRenderer:
    def render(self, analysis: IntentAnalysis, frame: ReasoningFrame, answer: str) -> str:
        clean_answer = self._clean(answer)
        return "\n\n".join(
            [
                "🧭 What I understood\n" + analysis.user_visible_summary,
                "🧠 How I analyzed it\n" + analysis.user_visible_analysis,
                "⚙️ How I decided to proceed\n" + frame.user_visible_decision,
                "💬 Answer\n" + clean_answer,
            ]
        )

    def fallback(self, analysis: IntentAnalysis, frame: ReasoningFrame) -> str:
        return self.render(
            analysis,
            frame,
            "I can help with this, but I need to keep the answer general because the available context is limited.",
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

