from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IntentAnalysis:
    intent: str
    task_type: str
    ambiguities: list[str] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    user_visible_summary: str = ""
    user_visible_analysis: str = ""


class IntentAnalyzer:
    def analyze(self, user_text: str) -> IntentAnalysis:
        cleaned = " ".join(user_text.strip().split())
        task_type = self._task_type(cleaned)
        ambiguities = self._ambiguities(cleaned, task_type)
        missing_context = self._missing_context(cleaned, task_type)
        return IntentAnalysis(
            intent=cleaned,
            task_type=task_type,
            ambiguities=ambiguities,
            missing_context=missing_context,
            user_visible_summary=self._summary(cleaned, task_type),
            user_visible_analysis=self._analysis(task_type, ambiguities, missing_context),
        )

    def _task_type(self, text: str) -> str:
        lower = text.lower()
        if "?" in text or lower.startswith(("how", "what", "why", "when", "where", "who")):
            return "question"
        if lower.startswith(("write", "draft", "create", "make", "generate")):
            return "creation"
        if lower.startswith(("fix", "debug", "improve", "review")):
            return "revision"
        if lower.startswith(("compare", "choose", "decide")):
            return "decision"
        return "general"

    def _ambiguities(self, text: str, task_type: str) -> list[str]:
        ambiguities: list[str] = []
        if len(text.split()) < 4:
            ambiguities.append("The request is brief, so there may be unstated preferences.")
        if task_type in {"creation", "revision"} and not any(
            marker in text.lower() for marker in ("tone", "format", "length", "audience")
        ):
            ambiguities.append("The desired style and level of detail are not fully specified.")
        return ambiguities

    def _missing_context(self, text: str, task_type: str) -> list[str]:
        missing: list[str] = []
        if task_type == "decision" and "between" not in text.lower():
            missing.append("The options or evaluation criteria may need to be inferred.")
        return missing

    def _summary(self, text: str, task_type: str) -> str:
        if task_type == "question":
            return "You are asking for a clear answer to your question."
        if task_type == "creation":
            return "You want me to create something useful from your request."
        if task_type == "revision":
            return "You want help improving or correcting something."
        if task_type == "decision":
            return "You want help making or explaining a decision."
        return "You want a helpful response to your message."

    def _analysis(self, task_type: str, ambiguities: list[str], missing_context: list[str]) -> str:
        parts = [f"I treated this as a {task_type} task and separated the main goal from any assumptions."]
        if ambiguities:
            parts.append("Some details are open, so I used reasonable defaults instead of stopping.")
        if missing_context:
            parts.append("Where context was missing, I stayed conservative and avoided inventing specifics.")
        return " ".join(parts)

