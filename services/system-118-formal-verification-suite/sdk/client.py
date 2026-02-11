"""SDK client placeholder for formal-verification-suite."""

from dataclasses import dataclass


@dataclass
class System118Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
