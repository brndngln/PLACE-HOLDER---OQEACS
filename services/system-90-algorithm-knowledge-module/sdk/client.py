"""SDK client placeholder for algorithm-knowledge-module."""

from dataclasses import dataclass


@dataclass
class System90Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
