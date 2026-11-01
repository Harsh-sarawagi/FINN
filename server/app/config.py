from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FINN Investment Intelligence API"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/finn"
    openai_api_key: str = ""
    openai_model: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    ai_api_key: str = ""
    ai_api_url: str = ""
    ai_model_name: str = ""
    scheduler_enabled: bool = True
    market_ingestion_interval_minutes: int = 60
    announcement_ingestion_interval_minutes: int = 30
    scheduler_run_on_startup: bool = False
    sse_heartbeat_seconds: int = 15

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_api_key(self) -> str:
        return self.ai_api_key or self.openai_api_key

    @property
    def llm_api_url(self) -> str:
        if self.ai_api_url:
            return self.ai_api_url
        if self.ai_api_key:
            return "https://api.groq.com/openai/v1/chat/completions"
        return "https://api.openai.com/v1/chat/completions"

    @property
    def llm_model(self) -> str:
        return self.ai_model_name or self.openai_model or "gpt-4o-mini"

@lru_cache
def get_settings() -> Settings:
    return Settings()
