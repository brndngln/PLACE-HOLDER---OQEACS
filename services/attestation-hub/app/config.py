from functools import lru_cache
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "attestation-hub"
    service_port: int = 9653
    log_level: str = "INFO"

    data_path: str = "/tmp/attestation-hub-store.json"
    attestation_hmac_key: str = "change-me"
    default_builder_id: str = "omni.build-fabric/v1"

    @property
    def log_level_int(self) -> int:
        return getattr(logging, self.log_level.upper(), logging.INFO)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
