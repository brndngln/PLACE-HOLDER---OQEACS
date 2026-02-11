"""SDK client placeholder for service-virtualization."""

from dataclasses import dataclass


@dataclass
class System123Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
