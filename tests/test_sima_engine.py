from sima.engine import IntentEngine


def test_sima_visible_summary_varies_by_task_type() -> None:
    engine = IntentEngine()
    cases = {
        "question": "What is PostgreSQL?",
        "creation": "Write a short launch announcement",
        "revision": "Fix this sentence",
        "decision": "Compare tea between coffee",
        "general": "Tell me about deployment",
    }

    analyses = {task_type: engine.analyze(text) for task_type, text in cases.items()}

    assert set(analyses) == {analysis.task_type for analysis in analyses.values()}
    assert len({analysis.user_visible_summary for analysis in analyses.values()}) == len(cases)
    assert len({tuple(analysis.opers) for analysis in analyses.values()}) == len(cases)
    assert all("helpful response" not in analysis.user_visible_summary.lower() for analysis in analyses.values())
    assert all("respond helpfully" not in " ".join(analysis.opers).lower() for analysis in analyses.values())


def test_sima_visible_analysis_varies_by_task_type() -> None:
    engine = IntentEngine()
    analyses = [
        engine.analyze("What is PostgreSQL?"),
        engine.analyze("Write a short launch announcement"),
        engine.analyze("Fix this sentence"),
        engine.analyze("Compare tea between coffee"),
        engine.analyze("Tell me about deployment"),
    ]

    assert len({analysis.user_visible_analysis for analysis in analyses}) == len(analyses)

