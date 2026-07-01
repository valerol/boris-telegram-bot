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
        parsed = sima_run(user_text)
        return IntentAnalysis(
            intent=str(parsed["intent"]),
            opers=list(parsed["opers"]),
            uncertainty=float(parsed["uncertainty"]),
            missing_info=list(parsed["missing_info"]),
        )

    def _intent(self, text: str) -> str:
        return _classify_intent(text)

    def _opers(self, text: str, intent: str) -> list[str]:
        return _keywords(text)

    def _missing_info(self, text: str, intent: str) -> list[str]:
        return _missing_info(text, intent)

    def _uncertainty(self, text: str, missing_info: list[str]) -> float:
        score = 0.1
        if len(text.split()) < 4:
            score += 0.25
        score += min(0.18 * len(missing_info), 0.55)
        return min(round(score, 2), 1.0)


IntentAnalyzer = IntentEngine


def sima_run(text: str) -> dict[str, object]:
    cleaned = " ".join(text.strip().split())
    intent = _classify_intent(cleaned)
    missing_info = _missing_info(cleaned, intent)
    return {
        "intent": intent,
        "opers": _keywords(cleaned),
        "uncertainty": _uncertainty(cleaned, missing_info),
        "missing_info": missing_info,
    }


def _classify_intent(text: str) -> str:
    lower = text.lower()
    tokens = _keywords(lower)
    first = tokens[0] if tokens else ""

    system_markers = {
        "architecture",
        "архитектура",
        "runtime",
        "pipeline",
        "system",
        "система",
        "бот",
        "bot",
        "settings",
        "config",
        "status",
        "version",
    }
    explanation_verbs = {"explain", "tell", "describe", "clarify", "расскажи", "объясни", "опиши", "поясни"}
    creation_verbs = {
        "write",
        "draft",
        "create",
        "make",
        "generate",
        "build",
        "напиши",
        "создай",
        "создать",
        "сгенерируй",
        "сделай",
    }
    decision_markers = {
        "compare",
        "choose",
        "decide",
        "which",
        "should",
        "сравни",
        "выбери",
        "реши",
        "лучше",
        "вариант",
        "option",
        "between",
    }
    question_markers = {"how", "what", "why", "when", "where", "who", "как", "что", "почему", "когда", "где", "кто"}

    if lower.startswith(("/", "help", "settings", "config", "status", "version")):
        return "system_query"
    if first in creation_verbs:
        return "creation_request"
    if first in decision_markers or _contains_phrase(lower, ("что лучше", "should i")):
        return "decision_request"
    if first in explanation_verbs:
        return "explanation_request"
    if any(marker in tokens for marker in system_markers) and any(marker in tokens for marker in {"architecture", "архитектура", "runtime", "pipeline", "system", "система", "бот", "bot"}):
        return "system_query"
    if "?" in text or first in question_markers or any(marker in tokens for marker in question_markers):
        return "question"
    if any(marker in tokens for marker in decision_markers):
        return "decision_request"
    if any(marker in tokens for marker in creation_verbs):
        return "creation_request"
    if any(marker in tokens for marker in explanation_verbs):
        return "explanation_request"
    return _fallback_intent(tokens)


def _keywords(text: str) -> list[str]:
    words = [word.strip(".,!?;:()[]{}\"'").lower().replace("ё", "е") for word in text.split()]
    return [word for word in words if word][:5]


def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _fallback_intent(tokens: list[str]) -> str:
    if not tokens:
        return "system_query"
    if len(tokens) <= 2:
        return "question"
    if any(token.endswith(("ть", "ти")) for token in tokens):
        return "creation_request"
    if any(token in {"или", "vs"} for token in tokens):
        return "decision_request"
    return "explanation_request"


def _missing_info(text: str, intent: str) -> list[str]:
    lower = text.lower()
    missing: list[str] = []
    if len(text.split()) < 3:
        missing.append("scope")
    if intent == "creation_request" and not any(token in lower for token in ("tone", "format", "length", "аудитория", "тон", "формат")):
        missing.append("format")
    if intent == "decision_request" and not any(token in lower for token in ("between", "or", "vs", "или", "между")):
        missing.append("options")
    if intent == "system_query" and len(text.split()) < 2:
        missing.append("command_target")
    return missing


def _uncertainty(text: str, missing_info: list[str]) -> float:
    score = 0.15
    if len(text.split()) < 3:
        score += 0.2
    score += min(0.15 * len(missing_info), 0.45)
    return min(round(score, 2), 1.0)
