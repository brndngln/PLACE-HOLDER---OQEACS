"""SDK client placeholder for performance-profiling-suite."""

from dataclasses import dataclass


@dataclass
class System143Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
