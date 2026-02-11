"""SDK client placeholder for license-compliance-scanner."""

from dataclasses import dataclass


@dataclass
class System81Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
