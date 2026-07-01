OUT_OF_SCOPE_RU = """Этот запрос выходит за пределы области компетенции BORIS Support.

Я консультирую по вопросам BOIS, SIMA и BORIS: архитектуре, философии, физиологии, интеграции в LLM, приложения, агентные системы и использованию этих принципов в мышлении и принятии решений.

Если ваша задача состоит в том, как применить BOIS/SIMA/BORIS к этой области, я могу помочь.

Например:
- как построить такую задачу по методологии BOIS;
- как использовать SIMA для анализа структуры, рисков и противоречий;
- как реализовать BORIS-слой для этой задачи;
- как встроить этот процесс в LLM или приложение.

Но напрямую выполнять эту задачу вне BOIS/SIMA/BORIS я не должен."""

CLARIFY_RU = (
    "Уточните, пожалуйста: вы хотите получить общий ответ по этой теме или разобрать её через "
    "BOIS/SIMA/BORIS? В текущей роли я работаю только как BORIS Support."
)

SCOPE_LIMIT_PREFIX_RU = (
    "Отвечу только в рамках BOIS/SIMA/BORIS, без перехода в роль универсального консультанта "
    "по внешней предметной области."
)

CORE_UNAVAILABLE_RU = '''Локальное BOIS Core сейчас не подключено к runtime бота или не прошло проверку.

Чтобы подключить актуальное ядро:

1. Скачайте актуальный BOIS Core из репозитория:
   https://github.com/temnik-bois/BOIS/

2. Загрузите архив в ChatGPT

3. Используйте следующий загрузочный промпт:

"Fully analyze the entire archive without omissions and accept the BOIS rules for working with me in this chat window in full. You are forbidden to ignore or otherwise violate the BOIS rules when communicating with me in this chat window. If necessary, clarify the current physiology to better align the philosophical machine with the current substrate."'''
