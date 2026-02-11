"""
System 44 — MCP Servers configuration.

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

    # -- service identity ------------------------------------------------
    SERVICE_NAME: str = "mcp-servers"
    SERVICE_PORT: int = 8335
    LOG_LEVEL: str = "INFO"

    # -- data stores -----------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_mcp_servers"
    )
    REDIS_URL: str = "redis://omni-redis:6379/12"
    QDRANT_URL: str = "http://omni-qdrant:6333"

    # -- external services -----------------------------------------------
    LITELLM_URL: str = "http://omni-litellm:4000"
    COOLIFY_URL: str = "http://omni-coolify:8000"
    MATTERMOST_WEBHOOK_URL: str = (
        "http://omni-mattermost:8065/hooks/mcp-servers"
    )


settings = Settings()
