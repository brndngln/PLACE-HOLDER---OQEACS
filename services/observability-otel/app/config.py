from functools import lru_cache
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "observability-otel"
    service_port: int = 9651
    log_level: str = "INFO"

    data_path: str = "/tmp/observability-otel-state.json"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_collector_url: str = "http://localhost:13133"
    default_sampling_ratio: float = 0.2

    @property
    def log_level_int(self) -> int:
        return getattr(logging, self.log_level.upper(), logging.INFO)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
