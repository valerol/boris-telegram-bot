from boris.engine import ReasoningFrame
from sima.engine import IntentAnalysis
from trace.renderer import HumanTraceRenderer


def test_trace_renderer_uses_structured_sima_fields_only() -> None:
    analysis = IntentAnalysis(
        intent="decision",
        opers=["classify_decision", "extract_options"],
        uncertainty=0.46,
        missing_info=["decision_criteria"],
    )
    frame = ReasoningFrame(
        domain="Comparative reasoning",
        constraints=["Return only the direct answer text."],
        reasoning_frame="compare factors",
        user_visible_decision="unused narrative field",
    )

    output = HumanTraceRenderer().render(
        analysis,
        frame,
        "Choose the simpler option.",
        {"allowed": True, "risk": "low", "reason": "allowed"},
    )

    assert "- classify_decision" in output
    assert "- uncertainty: 0.46" in output
    assert "- missing info: decision_criteria" in output
    assert "- gate: allowed" in output
    assert "unused narrative field" not in output

