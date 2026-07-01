from __future__ import annotations

from dataclasses import asdict

from bois.gate import DecisionGate, GateDecision
from boris.structurer import ReasoningStructurer
from config.settings import Settings
from core.rendering import HumanTraceRenderer
from memory.models import ChatMessage
from memory.postgres import PostgresSessionStore
from qa.validator import ResponseValidator
from runtime.llm import LLMClient
from sima.analyzer import IntentAnalyzer

REFUSAL_TEXT = "I can’t proceed with this request."


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        store: PostgresSessionStore,
        llm: LLMClient,
        gate: DecisionGate | None = None,
        analyzer: IntentAnalyzer | None = None,
        structurer: ReasoningStructurer | None = None,
        renderer: HumanTraceRenderer | None = None,
        validator: ResponseValidator | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._llm = llm
        self._gate = gate or DecisionGate()
        self._analyzer = analyzer or IntentAnalyzer()
        self._structurer = structurer or ReasoningStructurer()
        self._renderer = renderer or HumanTraceRenderer()
        self._validator = validator or ResponseValidator()

    async def handle_message(self, user_id: int, chat_id: int, user_text: str) -> str:
        session = await self._store.get(user_id=user_id, chat_id=chat_id)

        gate_result = self._gate.evaluate(user_text)
        session.risk_level = gate_result.risk_level
        if gate_result.decision == GateDecision.STOP:
            await self._store.save(session.trimmed(self._settings.max_history_messages))
            return REFUSAL_TEXT

        analysis = self._analyzer.analyze(user_text)
        frame = self._structurer.structure(analysis, gate_result.risk_level)

        answer = await self._llm.complete(user_text, session.conversation_history, frame)
        rendered = self._renderer.render(analysis, frame, answer)

        if not self._validator.is_valid(rendered):
            answer = await self._llm.complete(user_text, session.conversation_history, frame)
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
            "intent": analysis.intent,
            "task_type": analysis.task_type,
            "ambiguities": analysis.ambiguities,
            "missing_context": analysis.missing_context,
            "frame": asdict(frame),
        }
        await self._store.save(session.trimmed(self._settings.max_history_messages))
        return rendered

