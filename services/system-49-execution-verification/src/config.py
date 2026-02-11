"""Configuration for System 49: Execution Verification Loop."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service identity
    SERVICE_NAME: str = "omni-exec-verify"
    SERVICE_PORT: int = 9653
    LOG_LEVEL: str = "INFO"

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://omni:omni@omni-postgres:5432/exec_verify"

    # Redis
    REDIS_URL: str = "redis://omni-redis:6379/15"

    # Sandbox configuration
    SANDBOX_IMAGE: str = "python:3.12-slim"
    EXECUTION_TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 5
    MAX_MEMORY_MB: int = 256

    # LiteLLM for AI code regeneration
    LITELLM_URL: str = "http://omni-litellm:4000"

    # Notifications
    MATTERMOST_WEBHOOK_URL: str = "http://omni-mattermost:8065/hooks/exec-verify"

    model_config = {"env_file": ".env", "extra": "ignore"}
