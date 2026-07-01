from __future__ import annotations

from bois.guard import DecisionGate
from boris.engine import ReasoningEngine, ReasoningFrame
from config.settings import Settings
from memory.models import ChatMessage
from memory.store import PostgresSessionStore
from qa.validator import ResponseValidator
from runtime.llm import LLMClient
from sima.engine import IntentAnalysis, IntentEngine
from trace.renderer import HumanTraceRenderer

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
        if not self._validator.is_answer_only(answer):
            answer = await self._safe_complete(
                user_text,
                session.conversation_history,
                analysis,
                frame,
                answer_only_retry=True,
            )
        if not self._validator.is_answer_only(answer):
            answer = (
                "I can help with this, but I need to keep the answer general because the generated answer "
                "did not match the required response boundary."
            )
        gate_snapshot = {
            "allowed": gate_result.allowed,
            "risk": gate_result.risk,
            "reason": gate_result.reason,
        }
        rendered = self._renderer.render(analysis, frame, answer, gate_snapshot)

        if not self._validator.is_valid(rendered):
            rendered = self._renderer.fallback(analysis, frame, gate_snapshot)

        session.conversation_history.extend(
            [
                ChatMessage(role="user", content=user_text),
                ChatMessage(role="assistant", content=rendered),
            ]
        )
        session.last_reasoning_context = {
            "gate": gate_snapshot,
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
                intent="general",
                opers=["classify_open_request", "select_response_mode"],
                uncertainty=0.7,
                missing_info=["intent_parse"],
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
                    "Return only the direct answer text.",
                    "Do not include headings, labels, or explanation sections.",
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
        answer_only_retry: bool = False,
    ) -> str:
        try:
            return await self._llm.complete(user_text, history, analysis, frame, answer_only_retry=answer_only_retry)
        except Exception:
            return "I can help with this, but I need to keep the answer general because the answer source was unavailable."
