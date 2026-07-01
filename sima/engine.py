from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IntentAnalysis:
    intent: str
    task_type: str
    opers: list[str] = field(default_factory=list)
    uncertainty_score: float = 0.0
    missing_information: list[str] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    user_visible_summary: str = ""
    user_visible_analysis: str = ""

    def to_snapshot(self) -> dict[str, object]:
        return self.to_dict()

    def to_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "task_type": self.task_type,
            "opers": self.opers,
            "uncertainty_score": self.uncertainty_score,
            "missing_information": self.missing_information,
        }


class IntentEngine:
    def analyze(self, user_text: str) -> IntentAnalysis:
        cleaned = " ".join(user_text.strip().split())
        task_type = self._task_type(cleaned)
        opers = self._opers(cleaned, task_type)
        missing_information = self._missing_information(cleaned, task_type)
        ambiguities = self._ambiguities(cleaned, task_type)
        uncertainty_score = self._uncertainty_score(cleaned, ambiguities, missing_information)
        return IntentAnalysis(
            intent=cleaned,
            task_type=task_type,
            opers=opers,
            uncertainty_score=uncertainty_score,
            missing_information=missing_information,
            ambiguities=ambiguities,
            missing_context=missing_information,
            user_visible_summary=self._summary(task_type),
            user_visible_analysis=self._analysis(task_type, uncertainty_score, missing_information),
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

    def _opers(self, text: str, task_type: str) -> list[str]:
        base = {
            "question": ["identify question", "answer directly"],
            "creation": ["infer desired artifact", "draft response"],
            "revision": ["locate issue", "propose correction"],
            "decision": ["identify options", "compare criteria", "recommend"],
            "general": ["classify open-ended request", "select direct response mode"],
        }
        opers = list(base.get(task_type, base["general"]))
        if len(text.split()) > 20:
            opers.insert(1, "summarize key details")
        return opers

    def _ambiguities(self, text: str, task_type: str) -> list[str]:
        ambiguities: list[str] = []
        if len(text.split()) < 4:
            ambiguities.append("The request is brief, so there may be unstated preferences.")
        if task_type in {"creation", "revision"} and not any(
            marker in text.lower() for marker in ("tone", "format", "length", "audience")
        ):
            ambiguities.append("The desired style and level of detail are not fully specified.")
        return ambiguities

    def _missing_information(self, text: str, task_type: str) -> list[str]:
        missing: list[str] = []
        if task_type == "decision" and "between" not in text.lower():
            missing.append("The options or evaluation criteria may need to be inferred.")
        return missing

    def _uncertainty_score(
        self,
        text: str,
        ambiguities: list[str],
        missing_information: list[str],
    ) -> float:
        score = 0.1
        if len(text.split()) < 4:
            score += 0.25
        score += min(0.2 * len(ambiguities), 0.4)
        score += min(0.2 * len(missing_information), 0.4)
        return min(round(score, 2), 1.0)

    def _summary(self, task_type: str) -> str:
        summaries = {
            "question": "You are asking a specific question that needs a direct answer.",
            "creation": "You are asking for a new piece of content to be drafted.",
            "revision": "You are asking to inspect existing material and improve it.",
            "decision": "You are asking to weigh options and choose a direction.",
            "general": "You are making an open-ended request without a fixed output type.",
        }
        return summaries.get(task_type, summaries["general"])

    def _analysis(
        self,
        task_type: str,
        uncertainty_score: float,
        missing_information: list[str],
    ) -> str:
        openings = {
            "question": "I identified the question being asked and separated the answer target from background details.",
            "creation": "I identified the artifact to create and inferred the likely format from the wording.",
            "revision": "I treated the request as an improvement task and looked for what needs to change.",
            "decision": "I treated the request as a choice task and looked for options, criteria, and tradeoffs.",
            "general": "I treated the request as open-ended and looked for the most concrete action implied by it.",
        }
        parts = [openings.get(task_type, openings["general"])]
        if uncertainty_score >= 0.4:
            parts.append("Some details are open, so I used cautious defaults instead of inventing specifics.")
        if missing_information:
            parts.append("Where context was missing, I kept the answer limited to what could be inferred.")
        return " ".join(parts)


IntentAnalyzer = IntentEngine
