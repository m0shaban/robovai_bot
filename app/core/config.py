from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # DB
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/robovai",
        validation_alias="DATABASE_URL",
    )

    # Security / Admin (for future hardening)
    secret_key: str = Field(default="change-me", validation_alias="SECRET_KEY")
    admin_password: str = Field(default="", validation_alias="ADMIN_PASSWORD")

    # CORS for widget embeds (comma-separated list, or '*' for all)
    cors_allow_origins: str = Field(default="*", validation_alias="CORS_ALLOW_ORIGINS")

    # LLM (OpenAI-compatible endpoints; works for Groq, many NVIDIA endpoints, etc.)
    llm_base_url: str = Field(
        default="https://api.groq.com/openai/v1", validation_alias="LLM_BASE_URL"
    )
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_model: str = Field(
        default="llama-3.1-70b-versatile", validation_alias="LLM_MODEL"
    )

    # Convenience alias requested: GROQ_API_KEY can be used instead of LLM_API_KEY
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    # Webhook behavior
    webhook_timeout_seconds: float = Field(
        default=5.0, validation_alias="WEBHOOK_TIMEOUT"
    )

    def effective_llm_api_key(self) -> str:
        return self.llm_api_key or self.groq_api_key


def admin_auth_enabled() -> bool:
    return bool(settings.admin_password.strip())


settings = Settings()
