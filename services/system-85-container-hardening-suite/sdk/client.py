"""SDK client placeholder for container-hardening-suite."""

from dataclasses import dataclass


@dataclass
class System85Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
