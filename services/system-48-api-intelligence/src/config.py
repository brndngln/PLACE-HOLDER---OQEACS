"""Configuration for System 48B: Real-Time API Intelligence."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service identity
    SERVICE_NAME: str = "omni-api-intelligence"
    SERVICE_PORT: int = 9652
    LOG_LEVEL: str = "info"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://omni:omni@localhost:5432/api_intelligence"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/8"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"

    # LiteLLM
    LITELLM_URL: str = "http://localhost:4000"

    # Registry URLs
    PYPI_URL: str = "https://pypi.org"
    NPM_REGISTRY_URL: str = "https://registry.npmjs.org"
    CRATES_REGISTRY_URL: str = "https://crates.io/api/v1"

    # Scanning intervals
    SCAN_INTERVAL_HOURS: int = 6
    SECURITY_CHECK_INTERVAL_HOURS: int = 1

    # Notifications
    MATTERMOST_WEBHOOK_URL: str = "http://localhost:8065/hooks/api-intelligence"
    MATTERMOST_CHANNEL: str = "api-intelligence-alerts"


settings = Settings()
