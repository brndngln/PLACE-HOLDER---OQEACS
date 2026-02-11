"""SDK client placeholder for reproducible-builds."""

from dataclasses import dataclass


@dataclass
class System164Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
