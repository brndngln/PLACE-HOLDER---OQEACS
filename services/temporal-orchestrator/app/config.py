from functools import lru_cache
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "temporal-orchestrator"
    service_port: int = 9650
    log_level: str = "INFO"

    temporal_address: str = "omni-temporal:7233"
    temporal_namespace: str = "default"
    temporal_enabled: bool = False

    max_concurrent_runs: int = 200
    default_timeout_seconds: int = 600

    data_path: str = "/tmp/temporal-orchestrator-store.json"

    @property
    def log_level_int(self) -> int:
        return getattr(logging, self.log_level.upper(), logging.INFO)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
