"""SDK client placeholder for design-forge."""

from dataclasses import dataclass


@dataclass
class System167Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
