from __future__ import annotations

from dataclasses import dataclass

from sima.engine import IntentAnalysis


@dataclass(frozen=True, slots=True)
class ReasoningFrame:
    domain: str
    constraints: list[str]
    reasoning_frame: str
    user_visible_decision: str

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
        }


class ReasoningEngine:
    def structure(self, analysis: IntentAnalysis, risk: str) -> ReasoningFrame:
        structured = boris_run(analysis.to_dict())
        constraints = list(structured["constraints"])
        if risk != "low":
            constraints.append("limit certainty")
        return ReasoningFrame(
            domain=str(structured["domain"]),
            constraints=constraints,
            reasoning_frame="constraint_application",
            user_visible_decision="",
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


def boris_run(sima: dict[str, object]) -> dict[str, object]:
    intent = sima["intent"]
    if intent == "question":
        return {
            "domain": "qa",
            "constraints": ["be concise", "avoid hallucination"],
        }
    if intent == "explanation_request":
        return {
            "domain": "explanation",
            "constraints": ["define terms", "preserve scope", "avoid hallucination"],
        }
    if intent == "creation_request":
        return {
            "domain": "creation",
            "constraints": ["produce requested artifact", "respect missing_info"],
        }
    if intent == "decision_request":
        return {
            "domain": "decision",
            "constraints": ["compare options", "state tradeoffs", "avoid unsupported certainty"],
        }
    if intent == "system_query":
        return {
            "domain": "system",
            "constraints": ["answer operationally", "do not expose hidden state"],
        }

    return {
        "domain": "explanation",
        "constraints": ["define terms", "preserve scope", "avoid hallucination"],
    }
