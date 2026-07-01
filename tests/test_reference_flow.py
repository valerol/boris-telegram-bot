from bois.gate import bois_gate
from boris.engine import boris_run
from core.orchestrator import REFUSAL_TEXT, process_message
from domain.engine import domain_run
from memory.models import ChatMessage
from sima.engine import sima_run
from trace.renderer import render_trace


class FakeLLM:
    calls = 0

    async def complete(
        self,
        user_text: str,
        history: list[ChatMessage],
        analysis,
        reasoning_frame,
        answer_only_retry: bool = False,
    ) -> str:
        self.calls += 1
        return "Direct answer."


def test_reference_stage_outputs() -> None:
    bois = bois_gate("What now?", {})
    sima = sima_run("What now?")
    domain = domain_run(sima)
    boris = boris_run(sima, domain)

    assert bois == {"allowed": True, "reason": "ok", "risk": "low"}
    assert sima == {
        "intent": "question",
        "opers": ["what", "now"],
        "uncertainty": 0.5,
        "missing_info": ["scope"],
    }
    assert domain == {"domain": "qa", "signals": [], "confidence": 0.55}
    assert boris == {
        "domain": "qa",
        "constraints": ["be concise", "avoid hallucination"],
        "domain_signals": [],
        "domain_confidence": 0.55,
    }


def test_reference_trace_renderer() -> None:
    output = render_trace(
        "What now?",
        {"allowed": True, "reason": "ok", "risk": "low"},
        {"intent": "question", "opers": ["what", "now"], "uncertainty": 0.15, "missing_info": []},
        {"domain": "qa", "constraints": ["be concise", "avoid hallucination"]},
        "Direct answer.",
    )

    assert "Intent class: question." in output
    assert "- opers: what, now" in output
    assert "- risk: low" in output
    assert "- constraints: be concise, avoid hallucination" in output


async def test_process_message_stops_before_llm_when_blocked() -> None:
    llm = FakeLLM()
    response = await process_message(1, "hack this", {}, llm)

    assert response == REFUSAL_TEXT
    assert llm.calls == 0
