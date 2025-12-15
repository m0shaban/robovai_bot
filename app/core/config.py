from __future__ import annotations

from pydantic import Field, field_validator
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

    @field_validator("database_url")
    @classmethod
    def convert_postgres_url(cls, v: str) -> str:
        """Convert postgresql:// to postgresql+asyncpg:// for Render compatibility"""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

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
        # Default picked to be a common Groq model name; override via env.
        default="llama-3.3-70b-versatile", validation_alias="LLM_MODEL"
    )

    # Convenience alias requested: GROQ_API_KEY can be used instead of LLM_API_KEY
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    # Optional convenience aliases for model selection
    groq_model: str = Field(default="", validation_alias="GROQ_MODEL")
    
    # NVIDIA NIM API support
    nvidia_api_key: str = Field(default="", validation_alias="NVIDIA_API_KEY")

    # Optional convenience alias for NVIDIA model selection
    nvidia_model: str = Field(default="", validation_alias="NVIDIA_MODEL")

    # Webhook behavior
    webhook_timeout_seconds: float = Field(
        default=5.0, validation_alias="WEBHOOK_TIMEOUT"
    )

    # Email Settings
    smtp_host: str = Field(default="", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    smtp_tls: bool = Field(default=True, validation_alias="SMTP_TLS")
    
    email_from: str = Field(default="noreply@robovai.com", validation_alias="EMAIL_FROM")
    email_from_name: str = Field(default="RoboVAI", validation_alias="EMAIL_FROM_NAME")
    
    sendgrid_api_key: str = Field(default="", validation_alias="SENDGRID_API_KEY")

    def effective_llm_api_key(self) -> str:
        return self.llm_api_key or self.groq_api_key or self.nvidia_api_key

    def effective_llm_model(self) -> str:
        # Prefer explicit LLM_MODEL, then provider-specific aliases.
        return self.llm_model or self.groq_model or self.nvidia_model


def admin_auth_enabled() -> bool:
    return bool(settings.admin_password.strip())


settings = Settings()
