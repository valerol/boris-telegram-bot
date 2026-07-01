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
        return ReasoningFrame(
            domain=str(structured["domain"]),
            constraints=constraints,
            reasoning_frame="constraint_application",
            user_visible_decision="",
        )

    def _domain(self, task_type: str) -> str:
        domains = {
            "question": "Direct explanation",
            "creation": "Useful drafting",
            "revision": "Practical improvement",
            "decision": "Comparative reasoning",
            "general": "General assistance",
        }
        return domains.get(task_type, "General assistance")

    def _reasoning_frame(self, task_type: str) -> str:
        frames = {
            "question": "answer the core question first and add only necessary context",
            "creation": "produce a complete draft using sensible defaults",
            "revision": "identify the likely issue and provide a corrected version",
            "decision": "compare the meaningful factors and recommend a path",
            "general": "respond directly and keep assumptions visible",
        }
        return frames.get(task_type, frames["general"])


ReasoningStructurer = ReasoningEngine


def boris_run(sima: dict[str, object]) -> dict[str, object]:
    if sima["intent"] == "question":
        return {
            "domain": "qa",
            "constraints": ["be concise", "avoid hallucination"],
        }

    return {
        "domain": "general",
        "constraints": ["be neutral"],
    }
