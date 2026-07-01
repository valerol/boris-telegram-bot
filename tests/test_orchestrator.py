from __future__ import annotations

from config.settings import Settings
from core.orchestrator import REFUSAL_TEXT, Orchestrator
from memory.models import SessionState
from qa.validator import REQUIRED_HEADINGS


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

    def structure(self, analysis, risk):
        self.calls += 1
        raise AssertionError("Structurer must not run when gate blocks.")


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
    assert llm.reasoning_frame.to_snapshot()["domain"] == "Useful drafting"
    assert store.session.risk_level == "low"
    assert store.session.last_reasoning_context["intent"]["intent"] == "creation"
    assert store.session.state_snapshots
    assert store.session.execution_traces[-1]["steps"] == ["gate", "intent", "structure", "llm", "trace"]


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
    assert "I can help with this" in response


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
    def structure(self, analysis, risk):
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
