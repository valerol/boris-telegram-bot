from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IntentAnalysis:
    intent: str
    opers: list[str] = field(default_factory=list)
    uncertainty: float = 0.0
    missing_info: list[str] = field(default_factory=list)

    @property
    def task_type(self) -> str:
        return self.intent

    @property
    def uncertainty_score(self) -> float:
        return self.uncertainty

    @property
    def missing_information(self) -> list[str]:
        return self.missing_info

    @property
    def missing_context(self) -> list[str]:
        return self.missing_info

    def to_snapshot(self) -> dict[str, object]:
        return self.to_dict()

    def to_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "opers": self.opers,
            "uncertainty": self.uncertainty,
            "missing_info": self.missing_info,
        }


class IntentEngine:
    def analyze(self, user_text: str) -> IntentAnalysis:
        cleaned = " ".join(user_text.strip().split())
        intent = self._intent(cleaned)
        opers = self._opers(cleaned, intent)
        missing_info = self._missing_info(cleaned, intent)
        uncertainty = self._uncertainty(cleaned, missing_info)
        return IntentAnalysis(
            intent=intent,
            opers=opers,
            uncertainty=uncertainty,
            missing_info=missing_info,
        )

    def _intent(self, text: str) -> str:
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

    def _opers(self, text: str, intent: str) -> list[str]:
        base = {
            "question": ["classify_question", "extract_answer_target"],
            "creation": ["classify_artifact", "infer_output_format"],
            "revision": ["classify_revision", "locate_change_target"],
            "decision": ["classify_decision", "extract_options", "extract_criteria"],
            "general": ["classify_open_request", "select_response_mode"],
        }
        opers = list(base.get(intent, base["general"]))
        if len(text.split()) > 20:
            opers.insert(1, "compress_context")
        return opers

    def _missing_info(self, text: str, intent: str) -> list[str]:
        missing: list[str] = []
        if len(text.split()) < 4:
            missing.append("detail_level")
        if intent in {"creation", "revision"} and not any(
            marker in text.lower() for marker in ("tone", "format", "length", "audience")
        ):
            missing.append("style_constraints")
        if intent == "decision" and "between" not in text.lower():
            missing.append("decision_options")
            missing.append("decision_criteria")
        return missing

    def _uncertainty(self, text: str, missing_info: list[str]) -> float:
        score = 0.1
        if len(text.split()) < 4:
            score += 0.25
        score += min(0.18 * len(missing_info), 0.55)
        return min(round(score, 2), 1.0)


IntentAnalyzer = IntentEngine
