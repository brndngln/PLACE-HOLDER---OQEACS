"""System 46 — Configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "omni-debate-engine"
    SERVICE_PORT: int = 9650
    DATABASE_URL: str = "postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_debate"
    REDIS_URL: str = "redis://omni-redis:6379/14"
    LITELLM_URL: str = "http://omni-litellm:4000"
    QDRANT_URL: str = "http://omni-qdrant:6333"
    MATTERMOST_WEBHOOK_URL: str = "http://omni-mattermost:8065/hooks/debate-engine"
    LOG_LEVEL: str = "INFO"
    DEFAULT_MODEL: str = "gpt-4o"
    DEBATE_TIMEOUT_SECONDS: int = 120
    MAX_ROUNDS: int = 5
    MIN_CONSENSUS_SCORE: float = 0.75

    model_config = {"env_prefix": "", "case_sensitive": True}
