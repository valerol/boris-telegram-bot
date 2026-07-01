import inspect

from sima.engine import IntentAnalysis, IntentEngine


def test_sima_outputs_strict_structured_data() -> None:
    engine = IntentEngine()
    cases = {
        "question": "What is PostgreSQL?",
        "general": "Tell me about deployment",
    }

    analyses = {task_type: engine.analyze(text) for task_type, text in cases.items()}

    assert set(analyses) == {analysis.intent for analysis in analyses.values()}
    for analysis in analyses.values():
        assert set(analysis.to_dict()) == {"intent", "opers", "uncertainty", "missing_info"}
        assert isinstance(analysis.intent, str)
        assert analysis.opers
        assert 0.0 <= analysis.uncertainty <= 1.0
        assert all(" " not in field for field in analysis.missing_info)

    assert analyses["question"].to_dict() == {
        "intent": "question",
        "opers": ["What", "is", "PostgreSQL?"],
        "uncertainty": 0.4,
        "missing_info": [],
    }


def test_sima_contains_no_natural_language_reasoning_fields() -> None:
    assert not hasattr(IntentAnalysis("general"), "user_visible_summary")
    assert not hasattr(IntentAnalysis("general"), "user_visible_analysis")

    source = inspect.getsource(IntentEngine)
    forbidden = (
        "What I understood",
        "How I analyzed",
        "I treated this as",
        "You are asking",
        "helpful response",
        "respond helpfully",
    )
    assert all(phrase not in source for phrase in forbidden)
