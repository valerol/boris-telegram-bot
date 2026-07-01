import inspect

from sima.engine import IntentAnalysis, IntentEngine


def test_sima_outputs_strict_structured_data() -> None:
    engine = IntentEngine()
    cases = {
        "question": "What is PostgreSQL?",
        "explanation_request": "Расскажи о BOIS",
        "creation_request": "Write a short launch announcement",
        "decision_request": "Choose between tea or coffee",
        "system_query": "/status",
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
        "opers": ["what", "is", "postgresql"],
        "uncertainty": 0.15,
        "missing_info": [],
    }
    assert analyses["explanation_request"].intent != "general"
    assert analyses["explanation_request"].intent == "explanation_request"
    assert engine.analyze("Расскажи о BOIS").to_dict()["intent"] == "explanation_request"


def test_sima_contains_no_natural_language_reasoning_fields() -> None:
    assert not hasattr(IntentAnalysis("explanation_request"), "user_visible_summary")
    assert not hasattr(IntentAnalysis("explanation_request"), "user_visible_analysis")

    source = inspect.getsource(IntentEngine)
    forbidden = (
        "What I understood",
        "How I analyzed",
        "I treated this as",
        "You are asking",
        "helpful response",
        "respond helpfully",
        "general",
    )
    assert all(phrase not in source for phrase in forbidden)
