"""SDK client placeholder for ai-image-generator."""

from dataclasses import dataclass


@dataclass
class System168Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
