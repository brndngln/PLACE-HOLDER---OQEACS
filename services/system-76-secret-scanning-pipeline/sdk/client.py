"""SDK client placeholder for secret-scanning-pipeline."""

from dataclasses import dataclass


@dataclass
class System76Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
