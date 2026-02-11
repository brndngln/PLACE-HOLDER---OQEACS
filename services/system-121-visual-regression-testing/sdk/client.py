"""SDK client placeholder for visual-regression-testing."""

from dataclasses import dataclass


@dataclass
class System121Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
