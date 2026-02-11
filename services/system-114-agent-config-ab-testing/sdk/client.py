"""SDK client placeholder for agent-config-ab-testing."""

from dataclasses import dataclass


@dataclass
class System114Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
