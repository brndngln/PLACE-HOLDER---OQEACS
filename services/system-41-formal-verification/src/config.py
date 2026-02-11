"""System 41: Formal Verification Engine — Configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "formal-verification"
    SERVICE_PORT: int = 9634
    DATABASE_URL: str = "postgresql://omni:omni@omni-postgres:5432/omni_quantum"
    REDIS_URL: str = "redis://omni-redis:6379/0"
    MATTERMOST_WEBHOOK_URL: str = ""
    LITELLM_URL: str = "http://omni-litellm:4000"
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus"
    WORK_DIR: str = "/app/data/workdir"
    VERIFICATION_TIMEOUT_SECONDS: int = 300

    model_config = {"env_prefix": "", "case_sensitive": True}
