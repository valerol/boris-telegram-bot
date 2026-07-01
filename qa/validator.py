from __future__ import annotations

REQUIRED_HEADINGS = (
    "🧭 What I understood",
    "🧠 How I analyzed it",
    "⚙️ How I decided to proceed",
    "💬 Answer",
)

FORBIDDEN_VISIBLE_TERMS = (
    "BOIS",
    "SIMA",
    "BORIS",
    "pipeline",
    "runtime",
    "engine",
    "JSON",
    "schema",
)


class ResponseValidator:
    def is_valid(self, text: str) -> bool:
        return self.has_required_format(text) and not self.has_forbidden_terms(text)

    def has_required_format(self, text: str) -> bool:
        positions = []
        for heading in REQUIRED_HEADINGS:
            index = text.find(heading)
            if index == -1:
                return False
            positions.append(index)
        return positions == sorted(positions)

    def has_forbidden_terms(self, text: str) -> bool:
        upper_text = text.upper()
        return any(term.upper() in upper_text for term in FORBIDDEN_VISIBLE_TERMS)

