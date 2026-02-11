"""SDK client placeholder for delivery-pipeline."""

from dataclasses import dataclass


@dataclass
class System102Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
