from __future__ import annotations

from dataclasses import dataclass, field

from sima.engine import IntentAnalysis


@dataclass(frozen=True, slots=True)
class DomainFrame:
    domain: str
    signals: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_snapshot(self) -> dict[str, object]:
        return self.to_dict()

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "signals": self.signals,
            "confidence": self.confidence,
        }


class DomainEngine:
    def classify(self, analysis: IntentAnalysis) -> DomainFrame:
        parsed = domain_run(analysis.to_dict())
        return DomainFrame(
            domain=str(parsed["domain"]),
            signals=list(parsed["signals"]),
            confidence=float(parsed["confidence"]),
        )


def domain_run(sima: dict[str, object]) -> dict[str, object]:
    intent = str(sima.get("intent", "explanation_request"))
    opers = [str(oper).lower() for oper in sima.get("opers", [])]
    signals = _signals(opers)

    domain = _domain_from_signals(intent, signals)
    confidence = _confidence(intent, signals)
    return {
        "domain": domain,
        "signals": signals,
        "confidence": confidence,
    }


def _signals(opers: list[str]) -> list[str]:
    signal_map = {
        "architecture": {
            "architecture",
            "архитектура",
            "bois",
            "sima",
            "boris",
            "runtime",
            "pipeline",
            "слой",
            "layer",
            "система",
            "system",
            "bot",
            "бот",
        },
        "technical": {
            "python",
            "js",
            "javascript",
            "api",
            "postgres",
            "postgresql",
            "psql",
            "git",
            "commit",
            "push",
            "pull",
            "systemd",
            "telegram",
            "server",
            "сервер",
            "демон",
            "venv",
        },
        "business": {
            "business",
            "бизнес",
            "market",
            "рынок",
            "plan",
            "план",
            "strategy",
            "стратегия",
            "sales",
            "продажи",
        },
    }
    matched: list[str] = []
    for signal, markers in signal_map.items():
        if any(oper in markers for oper in opers):
            matched.append(signal)
    return matched


def _domain_from_signals(intent: str, signals: list[str]) -> str:
    if "architecture" in signals:
        return "architecture"
    if "technical" in signals:
        return "technical"
    if "business" in signals:
        return "business"
    if intent == "creation_request":
        return "creation"
    if intent == "decision_request":
        return "decision"
    if intent == "system_query":
        return "system"
    if intent == "question":
        return "qa"
    return "explanation"


def _confidence(intent: str, signals: list[str]) -> float:
    score = 0.55
    if intent in {"creation_request", "decision_request", "system_query"}:
        score += 0.15
    if signals:
        score += min(0.1 * len(signals), 0.25)
    return min(round(score, 2), 1.0)
