from functools import lru_cache
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "policy-engine"
    service_port: int = 9652
    log_level: str = "INFO"

    data_path: str = "/tmp/policy-engine-store.json"
    policies_dir: str = "/tmp/policy-engine-policies"
    opa_url: str = "http://localhost:8181"
    opa_sync_enabled: bool = False

    @property
    def log_level_int(self) -> int:
        return getattr(logging, self.log_level.upper(), logging.INFO)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
