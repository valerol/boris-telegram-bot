from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ChatMessage":
        return cls(role=str(value["role"]), content=str(value["content"]))


@dataclass(slots=True)
class SessionState:
    user_id: int
    chat_id: int
    conversation_history: list[ChatMessage] = field(default_factory=list)
    last_reasoning_context: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def trimmed(self, max_messages: int) -> "SessionState":
        if max_messages > 0:
            self.conversation_history = self.conversation_history[-max_messages:]
        return self

