"""SDK client placeholder for code-review-agent."""

from dataclasses import dataclass


@dataclass
class System107Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
