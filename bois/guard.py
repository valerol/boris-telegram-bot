from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GateDecision(StrEnum):
    PROCEED = "proceed"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class GateResult:
    allowed: bool
    risk: str
    reason: str

    def to_dict(self) -> dict[str, bool | str]:
        return {"allowed": self.allowed, "reason": self.reason, "risk": self.risk}

    @property
    def decision(self) -> GateDecision:
        return GateDecision.PROCEED if self.allowed else GateDecision.STOP

    @property
    def risk_level(self) -> str:
        return self.risk


class DecisionGate:
    """Deterministic hard gate that must run before all other processing."""

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

    _sensitive_terms = ("medical", "legal", "financial", "investment")

    def evaluate(self, user_text: str) -> GateResult:
        normalized = " ".join(user_text.lower().split())
        if not normalized:
            return GateResult(allowed=False, risk="low", reason="empty_request")
        if any(term in normalized for term in self._blocked_terms):
            return GateResult(allowed=False, risk="high", reason="disallowed_request")
        if any(term in normalized for term in self._sensitive_terms):
            return GateResult(allowed=True, risk="medium", reason="sensitive_domain")
        return GateResult(allowed=True, risk="low", reason="allowed")
