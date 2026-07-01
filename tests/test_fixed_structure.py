from __future__ import annotations

import inspect

from bois.gate import DecisionGate
from bot.main import build_application, main
from boris.engine import ReasoningEngine
from sima.engine import IntentEngine
from trace.renderer import HumanTraceRenderer


def test_fixed_modules_are_importable() -> None:
    assert DecisionGate
    assert IntentEngine
    assert ReasoningEngine
    assert HumanTraceRenderer
    assert callable(build_application)
    assert callable(main)


def test_trace_renderer_does_not_depend_on_llm() -> None:
    source = inspect.getsource(HumanTraceRenderer)
    assert "OpenAI" not in source
    assert "LLM" not in source
    assert ".complete(" not in source

