"""SDK client placeholder for knowledge-governance."""

from dataclasses import dataclass


@dataclass
class System97Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
