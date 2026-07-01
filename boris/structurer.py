from __future__ import annotations

from dataclasses import dataclass

from sima.analyzer import IntentAnalysis


@dataclass(frozen=True, slots=True)
class ReasoningFrame:
    domain_context: str
    constraints: list[str]
    strategy: str
    user_visible_decision: str


class ReasoningStructurer:
    def structure(self, analysis: IntentAnalysis, risk_level: str) -> ReasoningFrame:
        constraints = [
            "Answer in natural language.",
            "Do not reveal hidden implementation details.",
            "Use the required four-section response format.",
        ]
        if risk_level != "low":
            constraints.append("Keep the answer cautious and avoid overclaiming.")
        strategy = self._strategy(analysis.task_type)
        return ReasoningFrame(
            domain_context=self._domain_context(analysis.task_type),
            constraints=constraints,
            strategy=strategy,
            user_visible_decision=(
                f"I chose to {strategy}, while keeping the response clear and limited to what can be supported."
            ),
        )

    def _domain_context(self, task_type: str) -> str:
        contexts = {
            "question": "Direct explanation",
            "creation": "Useful drafting",
            "revision": "Practical improvement",
            "decision": "Comparative reasoning",
            "general": "General assistance",
        }
        return contexts.get(task_type, "General assistance")

    def _strategy(self, task_type: str) -> str:
        strategies = {
            "question": "answer the core question first and add only necessary context",
            "creation": "produce a complete draft using sensible defaults",
            "revision": "identify the likely issue and provide a corrected version",
            "decision": "compare the meaningful factors and recommend a path",
            "general": "respond directly and keep assumptions visible",
        }
        return strategies.get(task_type, strategies["general"])

