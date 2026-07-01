from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openai import AsyncOpenAI

from boris.structurer import ReasoningFrame
from memory.models import ChatMessage


class LLMClient(Protocol):
    async def complete(
        self,
        user_text: str,
        history: list[ChatMessage],
        reasoning_frame: ReasoningFrame,
    ) -> str:
        ...


@dataclass(slots=True)
class OpenAILLMClient:
    api_key: str
    model: str

    def __post_init__(self) -> None:
        self._client = AsyncOpenAI(api_key=self.api_key)

    async def complete(
        self,
        user_text: str,
        history: list[ChatMessage],
        reasoning_frame: ReasoningFrame,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise, careful assistant. Return only the final answer body, "
                    "without headings, hidden implementation terms, JSON, logs, or schemas."
                ),
            }
        ]
        for item in history[-10:]:
            messages.append({"role": item.role, "content": item.content})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Context: {reasoning_frame.domain_context}\n"
                    f"Approach: {reasoning_frame.strategy}\n"
                    f"User request: {user_text}"
                ),
            }
        )
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

