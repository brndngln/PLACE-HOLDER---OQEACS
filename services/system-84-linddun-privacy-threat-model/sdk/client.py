"""SDK client placeholder for linddun-privacy-threat-model."""

from dataclasses import dataclass


@dataclass
class System84Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
