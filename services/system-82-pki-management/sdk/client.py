"""SDK client placeholder for pki-management."""

from dataclasses import dataclass


@dataclass
class System82Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
