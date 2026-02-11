"""SDK client placeholder for event-bus."""

from dataclasses import dataclass


@dataclass
class System135Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
