"""SDK client placeholder for golden-test-suite."""

from dataclasses import dataclass


@dataclass
class System112Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
