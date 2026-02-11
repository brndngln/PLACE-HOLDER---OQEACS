"""SDK client placeholder for conference-talk-ingester."""

from dataclasses import dataclass


@dataclass
class System99Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
