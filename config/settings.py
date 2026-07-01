from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/reasoning_bot",
        alias="DATABASE_URL",
    )
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_history_messages: int = Field(default=20, alias="MAX_HISTORY_MESSAGES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

