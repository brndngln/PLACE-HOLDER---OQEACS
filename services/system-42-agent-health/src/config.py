"""
System 42 — Agent Health Monitor configuration.

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

    # ── service identity ────────────────────────────────────────────
    SERVICE_NAME: str = "agent-health"
    SERVICE_PORT: int = 9635
    LOG_LEVEL: str = "INFO"

    # ── data stores ─────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_agent_health"
    )
    REDIS_URL: str = "redis://omni-redis:6379/8"

    # ── external services ───────────────────────────────────────────
    LITELLM_URL: str = "http://omni-litellm:4000"
    MATTERMOST_WEBHOOK_URL: str = (
        "http://omni-mattermost:8065/hooks/agent-health"
    )
    SANDBOX_URL: str = "http://omni-sandbox:9620"


settings = Settings()
