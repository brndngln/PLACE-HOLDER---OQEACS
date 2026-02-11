"""SDK client placeholder for platform-knowledge-collections."""

from dataclasses import dataclass


@dataclass
class System91Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
