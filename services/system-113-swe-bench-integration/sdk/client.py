"""SDK client placeholder for swe-bench-integration."""

from dataclasses import dataclass


@dataclass
class System113Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
