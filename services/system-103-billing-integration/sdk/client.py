"""SDK client placeholder for billing-integration."""

from dataclasses import dataclass


@dataclass
class System103Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
