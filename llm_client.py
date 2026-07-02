import importlib
import os
import sys


def call_llm(text: str) -> str:
    """
    Формирует запрос в core.
    Включает системный BOIS регламент (из core).
    Возвращает текст ответа.
    """
    core_path = os.getenv("CORE_PATH")
    if core_path and core_path not in sys.path:
        sys.path.insert(0, core_path)

    module_name, function_name = os.getenv("CORE_LLM_CALLABLE", "core.llm:call_llm").split(":", 1)
    core_call_llm = getattr(importlib.import_module(module_name), function_name)
    return core_call_llm(text)
