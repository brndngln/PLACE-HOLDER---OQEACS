"""SDK client placeholder for flaky-test-quarantine."""

from dataclasses import dataclass


@dataclass
class System124Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
