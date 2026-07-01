from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from openai import AsyncOpenAI

from boris.engine import ReasoningFrame
from memory.models import ChatMessage
from sima.engine import IntentAnalysis


class LLMClient(Protocol):
    async def complete(
        self,
        user_text: str,
        history: list[ChatMessage],
        analysis: IntentAnalysis,
        reasoning_frame: ReasoningFrame,
        answer_only_retry: bool = False,
    ) -> str:
        ...


@dataclass(slots=True)
class OpenAILLMClient:
    api_key: str
    model: str
    _client: AsyncOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = AsyncOpenAI(api_key=self.api_key)

    async def complete(
        self,
        user_text: str,
        history: list[ChatMessage],
        analysis: IntentAnalysis,
        reasoning_frame: ReasoningFrame,
        answer_only_retry: bool = False,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise, careful assistant. Generate only the direct answer text. "
                    "Do not include headings, labels, sections, reasoning explanations, JSON, logs, or schemas. "
                    "Never write 'What I understood', 'How I analyzed it', 'How I decided to proceed', or 'Answer'."
                ),
            }
        ]
        if answer_only_retry:
            messages.append(
                {
                    "role": "system",
                    "content": "Answer only, no structure.",
                }
            )
        for item in history[-10:]:
            if item.role == "user":
                messages.append({"role": item.role, "content": item.content})
            elif item.role == "assistant":
                messages.append({"role": item.role, "content": _answer_part(item.content)})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Context: {reasoning_frame.domain_context}\n"
                    f"Intent: {analysis.intent}\n"
                    f"Actions: {', '.join(analysis.opers)}\n"
                    f"Uncertainty: {analysis.uncertainty_score}\n"
                    f"Missing information: {', '.join(analysis.missing_information) or 'none'}\n"
                    f"Constraints: {'; '.join(reasoning_frame.constraints)}\n"
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


def _answer_part(content: str) -> str:
    marker = "💬 Answer"
    if marker in content:
        return content.split(marker, 1)[1].strip()
    return content.strip()
