"""SDK client placeholder for accessibility-testing."""

from dataclasses import dataclass


@dataclass
class System162Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
