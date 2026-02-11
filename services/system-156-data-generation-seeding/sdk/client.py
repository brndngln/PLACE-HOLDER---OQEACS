"""SDK client placeholder for data-generation-seeding."""

from dataclasses import dataclass


@dataclass
class System156Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
