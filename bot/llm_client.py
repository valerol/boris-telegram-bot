from boris_runtime import BOISRuntime


_runtime = BOISRuntime()


def call_llm(text: str) -> str:
    """
    Формирует запрос в core.
    Включает системный BOIS регламент (из core).
    Возвращает текст ответа.
    """
    result = _runtime.run(text)
    return result["output"]["answer"]
