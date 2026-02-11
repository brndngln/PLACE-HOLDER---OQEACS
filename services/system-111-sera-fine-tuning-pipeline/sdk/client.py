"""SDK client placeholder for sera-fine-tuning-pipeline."""

from dataclasses import dataclass


@dataclass
class System111Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
