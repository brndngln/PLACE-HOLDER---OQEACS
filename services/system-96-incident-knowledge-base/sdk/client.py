"""SDK client placeholder for incident-knowledge-base."""

from dataclasses import dataclass


@dataclass
class System96Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
