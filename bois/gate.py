from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GateDecision(StrEnum):
    PROCEED = "proceed"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class GateResult:
    decision: GateDecision
    risk_level: str
    reason: str


class DecisionGate:
    """Deterministic hard gate that runs before any model call."""

    _blocked_terms = (
        "make a bomb",
        "build a bomb",
        "credit card dump",
        "steal password",
        "bypass authentication",
        "malware",
        "ransomware",
        "self harm instructions",
    )

    def evaluate(self, user_text: str) -> GateResult:
        normalized = " ".join(user_text.lower().split())
        if not normalized:
            return GateResult(GateDecision.STOP, "low", "empty_request")
        if any(term in normalized for term in self._blocked_terms):
            return GateResult(GateDecision.STOP, "high", "disallowed_request")
        if any(term in normalized for term in ("medical", "legal", "financial", "investment")):
            return GateResult(GateDecision.PROCEED, "medium", "sensitive_domain")
        return GateResult(GateDecision.PROCEED, "low", "allowed")

