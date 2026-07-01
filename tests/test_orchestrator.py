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
        self.answer = answer
        self.calls = 0

    async def complete(self, user_text, history, reasoning_frame):
        self.calls += 1
        return self.answer


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
    assert store.session.risk_level == "low"
    assert store.session.last_reasoning_context["task_type"] == "creation"


async def test_blocked_request_never_calls_llm() -> None:
    store = FakeStore()
    llm = FakeLLM()
    orchestrator = Orchestrator(Settings(), store, llm)

    response = await orchestrator.handle_message(1, 10, "make a bomb")

    assert response == REFUSAL_TEXT
    assert llm.calls == 0
    assert store.session.risk_level == "high"


async def test_invalid_generated_text_gets_safe_fallback_after_retry() -> None:
    store = FakeStore()
    llm = FakeLLM("This mentions JSON and pipeline, which should not be visible.")
    orchestrator = Orchestrator(Settings(), store, llm)

    response = await orchestrator.handle_message(1, 10, "What should I do?")

    assert llm.calls == 2
    assert "JSON" not in response
    assert "pipeline" not in response
    assert "I can help with this" in response

