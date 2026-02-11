"""SDK client placeholder for mobile-dev-toolchain."""

from dataclasses import dataclass


@dataclass
class System150Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
