"""SDK client placeholder for security-review-agent."""

from dataclasses import dataclass


@dataclass
class System108Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
