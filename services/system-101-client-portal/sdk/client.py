"""SDK client placeholder for client-portal."""

from dataclasses import dataclass


@dataclass
class System101Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
