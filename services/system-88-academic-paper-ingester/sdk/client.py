"""SDK client placeholder for academic-paper-ingester."""

from dataclasses import dataclass


@dataclass
class System88Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
