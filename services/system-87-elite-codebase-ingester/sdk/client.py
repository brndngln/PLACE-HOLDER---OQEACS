"""SDK client placeholder for elite-codebase-ingester."""

from dataclasses import dataclass


@dataclass
class System87Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
