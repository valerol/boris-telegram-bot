from qa.validator import ResponseValidator


def test_validator_accepts_required_format() -> None:
    text = (
        "🧭 What I understood\nIntent.\n\n"
        "🧠 How I analyzed it\nAnalysis.\n\n"
        "⚙️ How I decided to proceed\nDecision.\n\n"
        "💬 Answer\nAnswer."
    )
    assert ResponseValidator().is_valid(text)


def test_validator_rejects_hidden_terms() -> None:
    text = (
        "🧭 What I understood\nIntent.\n\n"
        "🧠 How I analyzed it\nAnalysis.\n\n"
        "⚙️ How I decided to proceed\nDecision.\n\n"
        "💬 Answer\nThis exposes BORIS."
    )
    assert not ResponseValidator().is_valid(text)

