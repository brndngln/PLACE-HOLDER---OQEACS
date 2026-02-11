"""SDK client placeholder for symbolic-execution-suite."""

from dataclasses import dataclass


@dataclass
class System119Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
