"""
System 43 — Self-Testing System configuration.

All settings are loaded from environment variables with safe defaults
for local development.  Production values MUST be injected via the
container environment or a mounted .env file.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration backed by environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # -- service identity ----------------------------------------------------
    SERVICE_NAME: str = "self-testing"
    SERVICE_PORT: int = 9636
    LOG_LEVEL: str = "INFO"

    # -- data stores ---------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_self_testing"
    )
    REDIS_URL: str = "redis://omni-redis:6379/9"

    # -- external services ---------------------------------------------------
    MATTERMOST_WEBHOOK_URL: str = (
        "http://omni-mattermost:8065/hooks/self-testing"
    )
    SANDBOX_URL: str = "http://omni-sandbox:9620"
    SCORING_URL: str = "http://omni-scoring:9623"
    RETROSPECTIVE_URL: str = "http://omni-retrospective:9633"


settings = Settings()
