BOIS_MARKERS = ("bois", "боис")
SIMA_MARKERS = ("sima", "сима")
BORIS_MARKERS = ("boris", "борис")

METHODOLOGY_MARKERS = (
    "применить",
    "через",
    "с точки зрения",
    "методолог",
    "methodology",
    "apply",
    "analyze through",
)

IMPLEMENTATION_MARKERS = (
    "реализ",
    "интегр",
    "runtime",
    "telegram",
    "bot",
    "бот",
    "llm",
    "agent",
    "прилож",
    "application",
    "saas",
    "desktop",
    "архитект",
    "protocol",
    "протокол",
)

BUSINESS_MARKERS = ("бизнес", "business", "магазин", "startup", "стартап", "маркет", "marketing")
PROGRAMMING_MARKERS = ("код", "python", "javascript", "api", "функц", "скрипт", "programming")
WRITING_MARKERS = ("напиши текст", "статья", "пост", "copy", "копирайт", "writing")
TRAVEL_MARKERS = ("путешеств", "travel", "отель", "маршрут", "flight", "билет")
MEDICAL_MARKERS = ("здоров", "болит", "medical", "doctor", "диагноз", "лечение")
LEGAL_MARKERS = ("юрист", "legal", "договор", "иск", "суд", "закон")
FINANCE_MARKERS = ("инвест", "finance", "кредит", "налог", "деньги", "акции")
RECIPE_MARKERS = ("рецепт", "recipe", "борщ", "суп", "приготов")


def resolve_domain(text: str) -> str:
    lower = text.lower()
    bois_related = is_bois_related(lower) or is_sima_related(lower) or is_boris_related(lower)

    if bois_related and _contains_any(lower, IMPLEMENTATION_MARKERS):
        return "bois_boris_implementation"
    if bois_related and _contains_any(lower, METHODOLOGY_MARKERS):
        return "bois_boris_methodology"
    if is_bois_related(lower):
        return "bois_core"
    if is_sima_related(lower):
        return "sima_analysis"
    if is_boris_related(lower):
        if "protocol" in lower or "протокол" in lower:
            return "boris_protocol"
        return "boris_runtime"
    if _contains_any(lower, ("llm", "openai", "model", "модель")):
        return "llm_integration" if bois_related else "programming_generic"
    if _contains_any(lower, BUSINESS_MARKERS):
        return "business_generic"
    if _contains_any(lower, RECIPE_MARKERS):
        return "recipe_generic"
    if _contains_any(lower, TRAVEL_MARKERS):
        return "travel_generic"
    if _contains_any(lower, MEDICAL_MARKERS):
        return "medical_generic"
    if _contains_any(lower, LEGAL_MARKERS):
        return "legal_generic"
    if _contains_any(lower, FINANCE_MARKERS):
        return "finance_generic"
    if _contains_any(lower, WRITING_MARKERS):
        return "writing_generic"
    if _contains_any(lower, PROGRAMMING_MARKERS):
        return "programming_generic"
    return "unknown"


def is_bois_related(text: str) -> bool:
    return _contains_any(text.lower(), BOIS_MARKERS)


def is_sima_related(text: str) -> bool:
    return _contains_any(text.lower(), SIMA_MARKERS)


def is_boris_related(text: str) -> bool:
    return _contains_any(text.lower(), BORIS_MARKERS)


def is_methodology_request(text: str) -> bool:
    return _contains_any(text.lower(), METHODOLOGY_MARKERS)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)
