"""SDK client placeholder for property-based-testing."""

from dataclasses import dataclass


@dataclass
class System115Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
