from __future__ import annotations

from bois.guard import DecisionGate
from boris.engine import ReasoningEngine, ReasoningFrame
from config.settings import Settings
from core.rendering import HumanTraceRenderer
from memory.models import ChatMessage
from memory.store import PostgresSessionStore
from qa.validator import ResponseValidator
from runtime.llm import LLMClient
from sima.engine import IntentAnalysis, IntentEngine

REFUSAL_TEXT = "I can’t proceed with this request."


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        store: PostgresSessionStore,
        llm: LLMClient,
        gate: DecisionGate | None = None,
        analyzer: IntentEngine | None = None,
        structurer: ReasoningEngine | None = None,
        renderer: HumanTraceRenderer | None = None,
        validator: ResponseValidator | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._llm = llm
        self._gate = gate or DecisionGate()
        self._analyzer = analyzer or IntentEngine()
        self._structurer = structurer or ReasoningEngine()
        self._renderer = renderer or HumanTraceRenderer()
        self._validator = validator or ResponseValidator()

    async def handle_message(self, user_id: int, chat_id: int, user_text: str) -> str:
        session = await self._store.get(user_id=user_id, chat_id=chat_id)

        gate_result = self._gate.evaluate(user_text)
        session.risk_level = gate_result.risk
        if not gate_result.allowed:
            session.execution_traces.append(
                {
                    "allowed": False,
                    "risk": gate_result.risk,
                    "reason": gate_result.reason,
                    "steps": ["gate"],
                }
            )
            await self._store.save(session.trimmed(self._settings.max_history_messages))
            return REFUSAL_TEXT

        analysis = self._safe_analyze(user_text)
        frame = self._safe_structure(analysis, gate_result.risk)

        answer = await self._safe_complete(user_text, session.conversation_history, analysis, frame)
        rendered = self._renderer.render(analysis, frame, answer)

        if not self._validator.is_valid(rendered):
            rendered = self._renderer.fallback(analysis, frame)

        session.conversation_history.extend(
            [
                ChatMessage(role="user", content=user_text),
                ChatMessage(role="assistant", content=rendered),
            ]
        )
        session.last_reasoning_context = {
            "gate": {
                "allowed": gate_result.allowed,
                "risk": gate_result.risk,
                "reason": gate_result.reason,
            },
            "intent": analysis.to_snapshot(),
            "structure": frame.to_snapshot(),
        }
        session.state_snapshots.append(session.last_reasoning_context)
        session.execution_traces.append(
            {
                "allowed": True,
                "risk": gate_result.risk,
                "reason": gate_result.reason,
                "steps": ["gate", "intent", "structure", "llm", "trace"],
            }
        )
        await self._store.save(session.trimmed(self._settings.max_history_messages))
        return rendered

    def _safe_analyze(self, user_text: str) -> IntentAnalysis:
        try:
            return self._analyzer.analyze(user_text)
        except Exception:
            return IntentAnalysis(
                intent=" ".join(user_text.strip().split()),
                task_type="general",
                opers=["interpret request", "respond helpfully"],
                uncertainty_score=0.7,
                missing_information=["Some request details could not be analyzed reliably."],
                ambiguities=["Some details are unclear."],
                missing_context=["Some request details could not be analyzed reliably."],
                user_visible_summary="You want a helpful response to your message.",
                user_visible_analysis=(
                    "Some details were unclear, so I used a cautious reading of your request."
                ),
            )

    def _safe_structure(self, analysis: IntentAnalysis, risk: str) -> ReasoningFrame:
        try:
            return self._structurer.structure(analysis, risk)
        except Exception:
            return ReasoningFrame(
                domain="General assistance",
                constraints=[
                    "Answer in natural language.",
                    "Do not reveal hidden implementation details.",
                    "Use the required four-section response format.",
                ],
                reasoning_frame="respond directly and keep assumptions visible",
                user_visible_decision=(
                    "I chose to respond directly and keep assumptions visible, while avoiding unsupported claims."
                ),
            )

    async def _safe_complete(
        self,
        user_text: str,
        history: list[ChatMessage],
        analysis: IntentAnalysis,
        frame: ReasoningFrame,
    ) -> str:
        try:
            return await self._llm.complete(user_text, history, analysis, frame)
        except Exception:
            return "I can help with this, but I need to keep the answer general because the answer source was unavailable."
