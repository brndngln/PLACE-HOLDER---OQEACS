"""SDK client placeholder for agent-role-definitions."""

from dataclasses import dataclass


@dataclass
class System104Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
