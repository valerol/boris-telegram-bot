from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import asyncpg

from memory.models import ChatMessage, SessionState


class PostgresSessionStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url)
        await self.ensure_schema()

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def ensure_schema(self) -> None:
        async with self._acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    user_id BIGINT PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    conversation_history JSONB NOT NULL DEFAULT '[]'::jsonb,
                    last_reasoning_context JSONB NOT NULL DEFAULT '{}'::jsonb,
                    risk_level TEXT NOT NULL DEFAULT 'low',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

    async def get(self, user_id: int, chat_id: int) -> SessionState:
        async with self._acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, chat_id, conversation_history, last_reasoning_context,
                       risk_level, updated_at
                FROM chat_sessions
                WHERE user_id = $1
                """,
                user_id,
            )
        if row is None:
            return SessionState(user_id=user_id, chat_id=chat_id)
        return SessionState(
            user_id=int(row["user_id"]),
            chat_id=int(row["chat_id"]),
            conversation_history=[
                ChatMessage.from_dict(item) for item in _json_value(row["conversation_history"])
            ],
            last_reasoning_context=dict(_json_value(row["last_reasoning_context"])),
            risk_level=str(row["risk_level"]),
            updated_at=row["updated_at"],
        )

    async def save(self, session: SessionState) -> None:
        session.updated_at = datetime.now(timezone.utc)
        async with self._acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_sessions (
                    user_id, chat_id, conversation_history, last_reasoning_context,
                    risk_level, updated_at
                )
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6)
                ON CONFLICT (user_id) DO UPDATE SET
                    chat_id = EXCLUDED.chat_id,
                    conversation_history = EXCLUDED.conversation_history,
                    last_reasoning_context = EXCLUDED.last_reasoning_context,
                    risk_level = EXCLUDED.risk_level,
                    updated_at = EXCLUDED.updated_at
                """,
                session.user_id,
                session.chat_id,
                json.dumps([message.to_dict() for message in session.conversation_history]),
                json.dumps(session.last_reasoning_context),
                session.risk_level,
                session.updated_at,
            )

    def _acquire(self) -> asyncpg.pool.PoolAcquireContext:
        if self._pool is None:
            raise RuntimeError("PostgresSessionStore.connect() must be called first.")
        return self._pool.acquire()


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value

