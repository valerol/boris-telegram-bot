from __future__ import annotations

import logging

from bois.gate import bois_gate
from bois.guard import DecisionGate
from boris.engine import ReasoningEngine, ReasoningFrame, boris_run
from config.settings import Settings
from domain.engine import DomainEngine, DomainFrame, domain_run
from memory.models import ChatMessage
from memory.store import PostgresSessionStore
from qa.validator import ResponseValidator
from runtime.llm import LLMClient
from sima.engine import IntentAnalysis, IntentEngine, sima_run
from trace.renderer import HumanTraceRenderer, render_trace

REFUSAL_TEXT = "I can’t proceed with this request."
LOGGER = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        store: PostgresSessionStore,
        llm: LLMClient,
        gate: DecisionGate | None = None,
        analyzer: IntentEngine | None = None,
        domain_engine: DomainEngine | None = None,
        structurer: ReasoningEngine | None = None,
        renderer: HumanTraceRenderer | None = None,
        validator: ResponseValidator | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._llm = llm
        self._gate = gate or DecisionGate()
        self._analyzer = analyzer or IntentEngine()
        self._domain = domain_engine or DomainEngine()
        self._structurer = structurer or ReasoningEngine()
        self._renderer = renderer or HumanTraceRenderer()
        self._validator = validator or ResponseValidator()

    async def handle_message(self, user_id: int, chat_id: int, user_text: str) -> str:
        session = await self._store.get(user_id=user_id, chat_id=chat_id)

        gate_result = self._gate.evaluate(user_text, session)
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

        LOGGER.debug("PIPELINE_ACTIVE: BOIS -> SIMA -> DOMAIN -> BORIS -> LLM")
        analysis = self._safe_analyze(user_text)
        domain = self._safe_domain(analysis)
        frame = self._safe_structure(analysis, gate_result.risk, domain)

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
            answer = "Answer unavailable."
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
            "domain": domain.to_snapshot(),
            "structure": frame.to_snapshot(),
        }
        session.state_snapshots.append(session.last_reasoning_context)
        session.execution_traces.append(
            {
                "allowed": True,
                "risk": gate_result.risk,
                "reason": gate_result.reason,
                "steps": ["gate", "intent", "domain", "structure", "llm", "trace"],
            }
        )
        await self._store.save(session.trimmed(self._settings.max_history_messages))
        return rendered

    def _safe_analyze(self, user_text: str) -> IntentAnalysis:
        try:
            return self._analyzer.analyze(user_text)
        except Exception:
            return IntentAnalysis(
                intent="explanation_request",
                opers=["fallback", "intent_parse"],
                uncertainty=0.7,
                missing_info=["intent_parse"],
            )

    def _safe_domain(self, analysis: IntentAnalysis) -> DomainFrame:
        try:
            return self._domain.classify(analysis)
        except Exception:
            return DomainFrame(domain="explanation", signals=[], confidence=0.0)

    def _safe_structure(self, analysis: IntentAnalysis, risk: str, domain: DomainFrame) -> ReasoningFrame:
        try:
            return self._structurer.structure(analysis, risk, domain)
        except Exception:
            return ReasoningFrame(
                domain=domain.domain,
                constraints=[
                    "Return only the direct answer text.",
                    "Do not include headings, labels, or explanation sections.",
                ],
                reasoning_frame="fallback_constraints",
                user_visible_decision="",
                domain_signals=domain.signals,
                domain_confidence=domain.confidence,
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
            return "Answer unavailable."


async def process_message(user_id: int, text: str, state: object, llm: LLMClient) -> str:
    decision = bois_gate(text, state)

    if not decision["allowed"]:
        return REFUSAL_TEXT

    sima = sima_run(text)
    domain = domain_run(sima)
    boris = boris_run(sima, domain)
    analysis = IntentAnalysis(
        intent=str(sima["intent"]),
        opers=list(sima["opers"]),
        uncertainty=float(sima["uncertainty"]),
        missing_info=list(sima["missing_info"]),
    )
    frame = ReasoningFrame(
        domain=str(boris["domain"]),
        constraints=list(boris["constraints"]),
        reasoning_frame="constraint_application",
        user_visible_decision="",
        domain_signals=list(boris.get("domain_signals", [])),
        domain_confidence=float(boris.get("domain_confidence", 0.0)),
    )
    answer = await llm.complete(text, [], analysis, frame)
    return render_trace(text, decision, sima, boris, answer)
