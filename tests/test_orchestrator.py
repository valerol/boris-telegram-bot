from __future__ import annotations

import logging

from config.settings import Settings
from core.orchestrator import REFUSAL_TEXT, Orchestrator
from bois.guard import GateResult
from boris.engine import ReasoningFrame
from domain.engine import DomainFrame
from memory.models import SessionState
from qa.validator import REQUIRED_HEADINGS
from sima.engine import IntentAnalysis


class FakeStore:
    def __init__(self) -> None:
        self.session = SessionState(user_id=1, chat_id=10)
        self.saved = 0

    async def get(self, user_id: int, chat_id: int) -> SessionState:
        self.session.user_id = user_id
        self.session.chat_id = chat_id
        return self.session

    async def save(self, session: SessionState) -> None:
        self.saved += 1
        self.session = session


class FakeLLM:
    def __init__(self, answer: str = "Here is the helpful answer.") -> None:
        self.answers = [answer]
        self.calls = 0
        self.retry_flags = []

    async def complete(self, user_text, history, analysis, reasoning_frame, answer_only_retry=False):
        self.calls += 1
        self.retry_flags.append(answer_only_retry)
        self.analysis = analysis
        self.reasoning_frame = reasoning_frame
        index = min(self.calls - 1, len(self.answers) - 1)
        return self.answers[index]


class SequenceLLM(FakeLLM):
    def __init__(self, answers: list[str]) -> None:
        super().__init__(answers[0])
        self.answers = answers


class ExplodingAnalyzer:
    calls = 0

    def analyze(self, user_text):
        self.calls += 1
        raise AssertionError("Analyzer must not run when gate blocks.")


class ExplodingStructurer:
    calls = 0

    def structure(self, analysis, risk, domain=None):
        self.calls += 1
        raise AssertionError("Structurer must not run when gate blocks.")


class RecordingGate:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.state_seen = None

    def evaluate(self, user_text, state=None):
        self.order.append("bois")
        self.state_seen = state
        return GateResult(allowed=True, risk="low", reason="ok")


class RecordingAnalyzer:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    def analyze(self, user_text):
        self.order.append("sima")
        return IntentAnalysis(
            intent="explanation_request",
            opers=["explain"],
            uncertainty=0.15,
            missing_info=[],
        )


class RecordingStructurer:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    def structure(self, analysis, risk, domain):
        self.order.append("boris")
        return ReasoningFrame(
            domain=domain.domain,
            constraints=["define terms"],
            reasoning_frame="constraint_application",
            user_visible_decision="",
            domain_signals=domain.signals,
            domain_confidence=domain.confidence,
        )


class RecordingDomain:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    def classify(self, analysis):
        self.order.append("domain")
        return DomainFrame(domain="architecture", signals=["architecture"], confidence=0.75)


class RecordingLLM(FakeLLM):
    def __init__(self, order: list[str]) -> None:
        super().__init__("Layered answer.")
        self.order = order

    async def complete(self, user_text, history, analysis, reasoning_frame, answer_only_retry=False):
        self.order.append("llm")
        return await super().complete(user_text, history, analysis, reasoning_frame, answer_only_retry)


async def test_response_uses_required_human_trace_format() -> None:
    store = FakeStore()
    llm = FakeLLM("Use concise wording and keep the structure readable.")
    orchestrator = Orchestrator(Settings(), store, llm)

    response = await orchestrator.handle_message(1, 10, "Write a short welcome message")

    for heading in REQUIRED_HEADINGS:
        assert heading in response
    assert "BOIS" not in response
    assert "SIMA" not in response
    assert "BORIS" not in response
    assert llm.calls == 1
    assert llm.analysis.opers
    assert llm.reasoning_frame.to_snapshot()["domain"] == "creation"
    assert store.session.risk_level == "low"
    assert store.session.last_reasoning_context["intent"]["intent"] == "creation_request"
    assert store.session.state_snapshots
    assert store.session.last_reasoning_context["domain"]["domain"] == "creation"
    assert store.session.execution_traces[-1]["steps"] == ["gate", "intent", "domain", "structure", "llm", "trace"]


async def test_pipeline_calls_gate_first_with_session_and_preserves_order(caplog) -> None:
    order: list[str] = []
    store = FakeStore()
    gate = RecordingGate(order)
    llm = RecordingLLM(order)
    caplog.set_level(logging.DEBUG, logger="core.orchestrator")
    orchestrator = Orchestrator(
        Settings(),
        store,
        llm,
        gate=gate,
        analyzer=RecordingAnalyzer(order),
        domain_engine=RecordingDomain(order),
        structurer=RecordingStructurer(order),
    )

    response = await orchestrator.handle_message(1, 10, "Расскажи о BOIS")

    assert order == ["bois", "sima", "domain", "boris", "llm"]
    assert gate.state_seen is store.session
    assert "Layered answer." in response
    assert "PIPELINE_ACTIVE: BOIS -> SIMA -> DOMAIN -> BORIS -> LLM" in caplog.text


async def test_blocked_request_never_calls_llm() -> None:
    store = FakeStore()
    llm = FakeLLM()
    analyzer = ExplodingAnalyzer()
    structurer = ExplodingStructurer()
    orchestrator = Orchestrator(Settings(), store, llm, analyzer=analyzer, structurer=structurer)

    response = await orchestrator.handle_message(1, 10, "make a bomb")

    assert response == REFUSAL_TEXT
    assert llm.calls == 0
    assert analyzer.calls == 0
    assert structurer.calls == 0
    assert store.session.risk_level == "high"
    assert store.session.execution_traces[-1]["steps"] == ["gate"]


async def test_invalid_generated_text_gets_safe_fallback_after_retry() -> None:
    store = FakeStore()
    llm = FakeLLM("This mentions JSON and pipeline, which should not be visible.")
    orchestrator = Orchestrator(Settings(), store, llm)

    response = await orchestrator.handle_message(1, 10, "What should I do?")

    assert llm.calls == 1
    assert "JSON" not in response
    assert "pipeline" not in response
    assert "Answer unavailable." in response


async def test_structured_llm_answer_is_rejected_and_regenerated() -> None:
    store = FakeStore()
    llm = SequenceLLM(
        [
            "🧭 What I understood\nA structure that must not come from the model.\n\n💬 Answer\nBad.",
            "This is the direct answer only.",
        ]
    )
    orchestrator = Orchestrator(Settings(), store, llm)

    response = await orchestrator.handle_message(1, 10, "What is the next step?")

    assert llm.calls == 2
    assert llm.retry_flags == [False, True]
    assert response.count("🧭 What I understood") == 1
    assert "This is the direct answer only." in response
    assert "A structure that must not come from the model" not in response


class BrokenAnalyzer:
    def analyze(self, user_text):
        raise RuntimeError("broken")


class BrokenStructurer:
    def structure(self, analysis, risk, domain=None):
        raise RuntimeError("broken")


async def test_internal_failures_use_safe_structures_without_exposing_errors() -> None:
    store = FakeStore()
    llm = FakeLLM("A safe answer.")
    orchestrator = Orchestrator(
        Settings(),
        store,
        llm,
        analyzer=BrokenAnalyzer(),
        structurer=BrokenStructurer(),
    )

    response = await orchestrator.handle_message(1, 10, "hello")

    for heading in REQUIRED_HEADINGS:
        assert heading in response
    assert "broken" not in response
    assert llm.calls == 1
