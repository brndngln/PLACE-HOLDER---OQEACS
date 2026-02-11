"""SDK client placeholder for green-software."""

from dataclasses import dataclass


@dataclass
class System161Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
