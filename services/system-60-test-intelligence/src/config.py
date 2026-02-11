from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "omni-test-intel"
    SERVICE_PORT: int = 9660
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "postgresql+asyncpg://omni:omni@omni-postgres:5432/system_60_test_intelligence"
    REDIS_URL: str = "redis://omni-redis:6379/0"
    LITELLM_URL: str = "http://omni-litellm:4000"
    MATTERMOST_WEBHOOK_URL: str = "http://omni-mattermost:8065/hooks/placeholder"

    model_config = {"env_prefix": "", "case_sensitive": True}
