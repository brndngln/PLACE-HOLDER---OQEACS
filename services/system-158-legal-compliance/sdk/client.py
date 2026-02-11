"""SDK client placeholder for legal-compliance."""

from dataclasses import dataclass


@dataclass
class System158Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
