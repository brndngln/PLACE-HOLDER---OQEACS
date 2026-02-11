"""SDK client placeholder for protocol-linting."""

from dataclasses import dataclass


@dataclass
class System166Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
