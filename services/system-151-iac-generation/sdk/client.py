"""SDK client placeholder for iac-generation."""

from dataclasses import dataclass


@dataclass
class System151Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
