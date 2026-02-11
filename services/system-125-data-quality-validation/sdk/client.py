"""SDK client placeholder for data-quality-validation."""

from dataclasses import dataclass


@dataclass
class System125Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
