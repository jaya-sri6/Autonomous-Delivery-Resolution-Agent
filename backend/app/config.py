from functools import lru_cache
import os
from pathlib import Path
from tempfile import gettempdir

from pydantic import model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./delivery_agent.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "deterministic"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    max_retry_count: int = 2
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000,https://autonomous-delivery-resolution-agent.vercel.app"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=False, extra="ignore")

    @field_validator("max_retry_count", mode="before")
    @classmethod
    def default_empty_retry_count(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return 2
        return value

    @model_validator(mode="before")
    @classmethod
    def default_empty_database_url(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        app_env = values.get("app_env", os.getenv("APP_ENV", "development"))
        database_url = values.get("database_url", os.getenv("DATABASE_URL"))
        if database_url is None or (isinstance(database_url, str) and not database_url.strip()):
            temporary_database = Path(gettempdir(), "delivery_agent.db").as_posix()
            values["database_url"] = f"sqlite:///{temporary_database}" if app_env == "production" else "sqlite:///./delivery_agent.db"
        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()
