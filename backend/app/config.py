from functools import lru_cache

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
