"""SDK client placeholder for jepsen-distributed-testing."""

from dataclasses import dataclass


@dataclass
class System117Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
