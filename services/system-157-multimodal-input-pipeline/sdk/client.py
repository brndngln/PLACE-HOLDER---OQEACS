"""SDK client placeholder for multimodal-input-pipeline."""

from dataclasses import dataclass


@dataclass
class System157Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
