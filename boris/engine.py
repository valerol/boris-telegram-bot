from __future__ import annotations

from dataclasses import dataclass

from domain.engine import DomainFrame, domain_run
from sima.engine import IntentAnalysis


@dataclass(frozen=True, slots=True)
class ReasoningFrame:
    domain: str
    constraints: list[str]
    reasoning_frame: str
    user_visible_decision: str
    domain_signals: list[str] | None = None
    domain_confidence: float | None = None

    @property
    def domain_context(self) -> str:
        return self.domain

    @property
    def strategy(self) -> str:
        return self.reasoning_frame

    def to_snapshot(self) -> dict[str, object]:
        return self.to_dict()

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "constraints": self.constraints,
            "reasoning_frame": self.reasoning_frame,
            "domain_signals": self.domain_signals or [],
            "domain_confidence": self.domain_confidence,
        }


class ReasoningEngine:
    def structure(self, analysis: IntentAnalysis, risk: str, domain: DomainFrame | None = None) -> ReasoningFrame:
        domain_data = domain.to_dict() if domain else domain_run(analysis.to_dict())
        structured = boris_run(analysis.to_dict(), domain_data)
        constraints = list(structured["constraints"])
        if risk != "low":
            constraints.append("limit certainty")
        return ReasoningFrame(
            domain=str(structured["domain"]),
            constraints=constraints,
            reasoning_frame="constraint_application",
            user_visible_decision="",
            domain_signals=list(structured.get("domain_signals", [])),
            domain_confidence=float(structured.get("domain_confidence", 0.0)),
        )

    def _domain(self, task_type: str) -> str:
        domains = {
            "question": "qa",
            "explanation_request": "explanation",
            "creation_request": "creation",
            "decision_request": "decision",
            "system_query": "system",
        }
        return domains.get(task_type, "explanation")

    def _reasoning_frame(self, task_type: str) -> str:
        frames = {
            "question": "qa_constraints",
            "explanation_request": "explanation_constraints",
            "creation_request": "creation_constraints",
            "decision_request": "decision_constraints",
            "system_query": "system_constraints",
        }
        return frames.get(task_type, frames["explanation_request"])


ReasoningStructurer = ReasoningEngine


def boris_run(sima: dict[str, object], domain: dict[str, object] | None = None) -> dict[str, object]:
    domain_data = domain or domain_run(sima)
    domain_name = str(domain_data["domain"])
    intent = str(sima["intent"])
    constraints = _constraints_for(domain_name, intent)
    return {
        "domain": domain_name,
        "constraints": constraints,
        "domain_signals": list(domain_data.get("signals", [])),
        "domain_confidence": domain_data.get("confidence", 0.0),
    }


def _constraints_for(domain: str, intent: str) -> list[str]:
    domain_constraints = {
        "architecture": ["preserve architecture scope", "answer operationally", "avoid hidden state"],
        "technical": ["be precise", "include runnable steps", "avoid hallucination"],
        "business": ["state assumptions", "prefer actionable structure", "avoid unsupported certainty"],
        "creation": ["produce requested artifact", "respect missing_info"],
        "decision": ["compare options", "state tradeoffs", "avoid unsupported certainty"],
        "system": ["answer operationally", "do not expose hidden state"],
        "qa": ["be concise", "avoid hallucination"],
        "explanation": ["define terms", "preserve scope", "avoid hallucination"],
    }
    constraints = list(domain_constraints.get(domain, domain_constraints["explanation"]))
    if intent == "question" and "be concise" not in constraints:
        constraints.append("be concise")
    if intent == "explanation_request" and "define terms" not in constraints:
        constraints.append("define terms")
    return constraints
